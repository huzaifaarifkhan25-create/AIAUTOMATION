from app.models.business import Business, BusinessSearchRequest


def search_mock_businesses(request: BusinessSearchRequest) -> list[Business]:
    """Return fictional med spas for API development, without external requests."""
    if request.industry.casefold() not in {"med spa", "med spas", "medspa", "medspas"}:
        return []

    return [
        Business(
            name="Demo Glow Med Spa (Mock)",
            website="https://example.com/demo-glow-med-spa",
            phone=None,
            address=f"Mock address, {request.location}",
            rating=4.5,
            review_count=120,
        ),
        Business(
            name="Demo Renewal Med Spa (Mock)",
            website=None,
            phone=None,
            address=f"Mock address, {request.location}",
            rating=None,
            review_count=None,
        ),
    ]
