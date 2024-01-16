from datetime import datetime

from entity.models import CompanyPastName


def parse_date(date_str):
    # Handles different date formats and returns a date object
    formats = ["%Y.%m.%d", "%Y.%m", "%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}")


def get_company_name(companies, date_str):
    modified_names = []
    target_date = parse_date(date_str) if date_str else None

    for company in companies:
        company_name = company.name  # Default to current name

        if target_date:
            past_names = CompanyPastName.objects.filter(company=company)
            for past_name in past_names:
                start_date = parse_date(
                    getattr(past_name, "start_date") or "0001.01.01"
                )
                end_date = parse_date(getattr(past_name, "end_date") or "9999.12.31")

                if start_date <= target_date <= end_date:
                    company_name = past_name.name
                    break

        modified_names.append({"id": company.id, "name": company_name})

    return modified_names
