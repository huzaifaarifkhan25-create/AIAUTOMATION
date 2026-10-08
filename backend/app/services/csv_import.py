import csv
import io
import re
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError

from app.errors import AppError
from app.models.business import Business
from app.models.csv_import import CsvImportReport, ImportProvenance, ImportRowResult
from app.models.workflow import BusinessRecord, now

MAX_BYTES = 2_000_000
MAX_ROWS = 2000
MAX_COLUMNS = 80
ALIASES = {
    "name": {"name", "title", "businessname", "companyname", "placename"},
    "website": {"website", "site", "websiteurl", "businesswebsite"},
    "phone": {"phone", "phonenumber", "telephone", "businessphone"},
    "address": {"address", "fulladdress", "businessaddress", "formattedaddress"},
    "rating": {"rating", "reviewrating", "starrating", "averagerating"},
    "review_count": {"reviewcount", "reviews", "numberofreviews", "userstotal", "userratingcount"},
    "place_id": {"placeid", "googleplaceid"},
    "listing_url": {"link", "mapsurl", "googlemapsurl", "listingurl"},
}
EMPTY = {"", "n/a", "na", "null", "none", "-", "—"}


def identity(business):
    return "|".join(" ".join(value.split()).casefold() for value in (business.name, business.address))


def normalize_header(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def map_columns(headers, explicit):
    if len(headers) > MAX_COLUMNS or len(set(headers)) != len(headers) or any(not h or len(h) > 200 for h in headers):
        raise AppError(422, "invalid_csv_headers", "CSV headers must be unique, nonempty, at most 200 characters, with at most 80 columns")
    mapping = {}
    if set(explicit) - ALIASES.keys() or any(value not in headers for value in explicit.values()):
        raise AppError(422, "invalid_column_map", "Column mapping must use supported fields and exact CSV header names")
    for field, aliases in ALIASES.items():
        if field in explicit:
            mapping[field] = explicit[field]
            continue
        matches = [header for header in headers if normalize_header(header) in aliases]
        if len(matches) > 1:
            raise AppError(422, "ambiguous_columns", f"Multiple columns match {field}; supply an explicit column_map")
        if matches:
            mapping[field] = matches[0]
    if not {"name", "address"} <= mapping.keys():
        raise AppError(422, "missing_columns", "Map business name and address columns before importing")
    if len(set(mapping.values())) != len(mapping):
        raise AppError(422, "invalid_column_map", "A CSV column cannot map to multiple fields")
    return mapping


def optional(value):
    value = value.strip()
    return None if value.casefold() in EMPTY else value


def website_url(value):
    value = optional(value)
    if value is None:
        return None
    if len(value) > 2048 or any(character.isspace() for character in value):
        raise ValueError("Website must be a valid HTTP/HTTPS URL")
    if "://" not in value and not value.startswith("//"):
        value = "https://" + value
    elif value.startswith("//"):
        value = "https:" + value
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Website must be a valid HTTP/HTTPS URL without credentials")
    if parsed.hostname.lower() in {"google.com", "www.google.com", "maps.google.com"} and ("/maps" in parsed.path or parsed.hostname == "maps.google.com"):
        raise ValueError("A Google Maps listing URL is not the business website; map it to listing_url")
    try:
        parsed.port
    except ValueError:
        raise ValueError("Website has an invalid port") from None
    return value


def numeric_rating(value):
    value = optional(value)
    if value is None:
        return None
    return float(value.replace(",", "."))


def numeric_reviews(value, warnings):
    value = optional(value)
    if value is None:
        return None
    value = re.sub(r"\s+reviews?$", "", value, flags=re.I).strip()
    if re.fullmatch(r"\d+(?:[.,]\d+)?[kKmM]", value):
        warnings.append("Abbreviated review count retained in provenance; exact count is unknown")
        return None
    if not re.fullmatch(r"\d+|\d{1,3}(?:[, \u00a0]\d{3})+", value):
        raise ValueError("Review count must be a nonnegative integer or an abbreviated count")
    return int(re.sub(r"[, \u00a0]", "", value))


def parse_csv(data, explicit):
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AppError(422, "csv_encoding", "Export the file as UTF-8 CSV") from None
    if "\x00" in text:
        raise AppError(422, "invalid_csv", "CSV cannot contain null bytes")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text, newline=""), dialect=dialect, strict=True)
    try:
        raw_headers = next(reader)
        headers = [header.strip() for header in raw_headers]
        mapping = map_columns(headers, explicit)
        parsed_rows = []
        for values in reader:
            if not values or not any(value.strip() for value in values):
                continue
            if len(parsed_rows) >= MAX_ROWS:
                raise AppError(413, "csv_too_many_rows", "Import at most 2000 nonempty rows per file")
            row_number = reader.line_num
            if len(values) != len(headers):
                parsed_rows.append((ImportRowResult(row_number=row_number, status="invalid", errors=["Row has a different number of columns than the header"]), None))
                continue
            raw = dict(zip(headers, values))
            original = {field: raw[header] for field, header in mapping.items()}
            warnings = []
            try:
                if any(len(value) > 8192 for value in original.values()):
                    raise ValueError("Mapped values exceed the supported length")
                business = Business(
                    name=original["name"], address=original["address"],
                    website=website_url(original.get("website", "")),
                    phone=optional(original.get("phone", "")),
                    rating=numeric_rating(original.get("rating", "")),
                    review_count=numeric_reviews(original.get("review_count", ""), warnings),
                )
                if original.get("place_id") and len(original["place_id"].strip()) > 256:
                    raise ValueError("Place ID exceeds 256 characters")
                if len(original.get("listing_url", "")) > 2048:
                    raise ValueError("Listing URL exceeds 2048 characters")
                result = ImportRowResult(row_number=row_number, status="valid", business=business, warnings=warnings)
                parsed_rows.append((result, original))
            except ValidationError as error:
                errors = [f'{".".join(str(part) for part in e["loc"])}: {e["msg"]}' for e in error.errors(include_input=False, include_url=False)]
                parsed_rows.append((ImportRowResult(row_number=row_number, status="invalid", errors=errors), None))
            except (ValueError, OverflowError):
                parsed_rows.append((ImportRowResult(row_number=row_number, status="invalid", errors=["Invalid website, rating, review count, provider ID, or mapped field length"]), None))
        if not parsed_rows:
            raise AppError(422, "empty_csv", "CSV must contain at least one nonempty business row")
        return mapping, headers, parsed_rows
    except StopIteration:
        raise AppError(422, "empty_csv", "CSV must include a header and business rows") from None
    except csv.Error:
        raise AppError(422, "invalid_csv", "CSV syntax is invalid or a field is too large; no rows were imported") from None


async def import_csv(store, data, source, dry_run, collected_at, file_name, explicit):
    # Serialize identity checks with manual/provider saves in the single-worker MVP.
    async with store.business_lock:
        return await _import_csv(store, data, source, dry_run, collected_at, file_name, explicit)


async def _import_csv(store, data, source, dry_run, collected_at, file_name, explicit):
    if len(data) > MAX_BYTES:
        raise AppError(413, "csv_too_large", "CSV must be at most 2 MB")
    if collected_at > now():
        raise AppError(422, "future_collection_date", "Collection date cannot be in the future")
    mapping, headers, parsed_rows = parse_csv(data, explicit)
    # Parse the entire file before writing, so malformed syntax never partially imports.
    existing = [BusinessRecord.model_validate(record) for record in await store.list("businesses")]
    known_identities = {identity(record.business): record.id for record in existing}
    known_places = {record.provenance.place_id: record.id for record in existing if record.provenance and record.provenance.place_id}
    known_ids = {record.id for record in existing}
    imported = 0
    for result, original in parsed_rows:
        if result.status == "invalid":
            continue
        key = identity(result.business)
        place_id = optional(original.get("place_id", ""))
        duplicate_id = known_places.get(place_id) if place_id else None
        duplicate_id = duplicate_id or known_identities.get(key)
        if duplicate_id:
            result.status, result.business_id = "duplicate", duplicate_id
            continue
        record_id = str(uuid5(NAMESPACE_URL, "google_maps:place_id:" + place_id if place_id else "medspa:" + key))
        if record_id in known_ids:
            result.status, result.business_id = "duplicate", record_id
            continue
        provenance = ImportProvenance(
            source=source, collected_at=collected_at,
            file_name=file_name.replace("\\", "/").rsplit("/", 1)[-1],
            place_id=place_id, listing_url=optional(original.get("listing_url", "")),
            column_map=mapping, original_values=original,
        )
        timestamp = now()
        record = BusinessRecord(id=record_id, business=result.business, source=source,
                                created_at=timestamp, updated_at=timestamp, provenance=provenance)
        if not dry_run:
            try:
                reserved = await store.reserve("businesses", record_id, record.model_dump(mode="json"))
            except AppError as error:
                raise AppError(error.status_code, "csv_import_interrupted", f"Import interrupted after {imported} rows saved; retry the file to safely skip existing records") from None
            if not reserved:
                result.status, result.business_id = "duplicate", record_id
                known_identities[key] = record_id
                known_ids.add(record_id)
                if place_id:
                    known_places[place_id] = record_id
                continue
            result.status = "imported"
            imported += 1
        result.business_id = record_id
        known_identities[key] = record_id
        known_ids.add(record_id)
        if place_id:
            known_places[place_id] = record_id
    rows = [row for row, _ in parsed_rows]
    return CsvImportReport(
        dry_run=dry_run, source=source, total_rows=len(rows),
        valid_rows=sum(row.status in {"valid", "imported"} for row in rows),
        imported_rows=imported, duplicate_rows=sum(row.status == "duplicate" for row in rows),
        invalid_rows=sum(row.status == "invalid" for row in rows),
        column_map=mapping, ignored_columns=[header for header in headers if header not in mapping.values()],
        rows=rows,
    )
