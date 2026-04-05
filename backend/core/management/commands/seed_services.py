from django.core.management.base import BaseCommand
from core.models import Service, Company


SERVICES_DATA = [
    {
        "name": "Flights",
        "icon": "✈️",
        "companies": [
            {
                "name": "Southwest Airlines",
                "icon": "🟧",
                "form_schema": [
                    {"key": "from_city", "label": "From which city?", "type": "text", "required": True},
                    {"key": "to_city", "label": "To which city?", "type": "text", "required": True},
                    {"key": "travel_date", "label": "Travel date? (DD/MM/YYYY)", "type": "date", "required": True},
                    {"key": "return_date", "label": "Return date? (DD/MM/YYYY, or type 'one-way')", "type": "text", "required": False},
                    {"key": "passengers", "label": "Number of passengers?", "type": "number", "required": True},
                    {"key": "class_type", "label": "Class?", "type": "choice", "options": ["Economy", "Business"], "required": True},
                    {"key": "issue", "label": "Describe your request or issue:", "type": "text", "required": True},
                ],
            },
            {
                "name": "American Airlines",
                "icon": "🦅",
                "form_schema": [
                    {"key": "booking_ref", "label": "Booking reference (if any):", "type": "text", "required": False},
                    {"key": "from_city", "label": "From which city?", "type": "text", "required": True},
                    {"key": "to_city", "label": "To which city?", "type": "text", "required": True},
                    {"key": "travel_date", "label": "Travel date? (DD/MM/YYYY)", "type": "date", "required": True},
                    {"key": "passengers", "label": "Number of passengers?", "type": "number", "required": True},
                    {"key": "class_type", "label": "Class?", "type": "choice", "options": ["Economy", "Premium Economy", "Business", "First"], "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Frontier Airlines",
                "icon": "🦌",
                "form_schema": [
                    {"key": "from_city", "label": "From which city?", "type": "text", "required": True},
                    {"key": "to_city", "label": "To which city?", "type": "text", "required": True},
                    {"key": "travel_date", "label": "Travel date?", "type": "date", "required": True},
                    {"key": "passengers", "label": "Number of passengers?", "type": "number", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Spirit Airlines",
                "icon": "💛",
                "form_schema": [
                    {"key": "from_city", "label": "From which city?", "type": "text", "required": True},
                    {"key": "to_city", "label": "To which city?", "type": "text", "required": True},
                    {"key": "travel_date", "label": "Travel date?", "type": "date", "required": True},
                    {"key": "passengers", "label": "Passengers?", "type": "number", "required": True},
                    {"key": "bags", "label": "Need checked bags?", "type": "choice", "options": ["Yes", "No"], "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
        ],
    },
    {
        "name": "Hotels",
        "icon": "🏨",
        "companies": [
            {
                "name": "Marriott",
                "icon": "🏨",
                "form_schema": [
                    {"key": "city", "label": "Which city?", "type": "text", "required": True},
                    {"key": "check_in", "label": "Check-in date?", "type": "date", "required": True},
                    {"key": "check_out", "label": "Check-out date?", "type": "date", "required": True},
                    {"key": "guests", "label": "Number of guests?", "type": "number", "required": True},
                    {"key": "rooms", "label": "Number of rooms?", "type": "number", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Hilton",
                "icon": "🌟",
                "form_schema": [
                    {"key": "city", "label": "Which city?", "type": "text", "required": True},
                    {"key": "check_in", "label": "Check-in date?", "type": "date", "required": True},
                    {"key": "check_out", "label": "Check-out date?", "type": "date", "required": True},
                    {"key": "guests", "label": "Number of guests?", "type": "number", "required": True},
                    {"key": "room_type", "label": "Room type?", "type": "choice", "options": ["Standard", "Deluxe", "Suite"], "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Airbnb",
                "icon": "🏠",
                "form_schema": [
                    {"key": "location", "label": "Where are you looking?", "type": "text", "required": True},
                    {"key": "check_in", "label": "Check-in date?", "type": "date", "required": True},
                    {"key": "check_out", "label": "Check-out date?", "type": "date", "required": True},
                    {"key": "guests", "label": "Number of guests?", "type": "number", "required": True},
                    {"key": "property_type", "label": "Property type?", "type": "choice", "options": ["Entire place", "Private room", "Shared room"], "required": True},
                    {"key": "budget", "label": "Budget per night?", "type": "text", "required": False},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
        ],
    },
    {
        "name": "Stays",
        "icon": "🛏️",
        "companies": [
            {
                "name": "Booking.com",
                "icon": "🔵",
                "form_schema": [
                    {"key": "destination", "label": "Destination?", "type": "text", "required": True},
                    {"key": "check_in", "label": "Check-in date?", "type": "date", "required": True},
                    {"key": "check_out", "label": "Check-out date?", "type": "date", "required": True},
                    {"key": "guests", "label": "Guests?", "type": "number", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "VRBO",
                "icon": "🏡",
                "form_schema": [
                    {"key": "destination", "label": "Destination?", "type": "text", "required": True},
                    {"key": "check_in", "label": "Check-in date?", "type": "date", "required": True},
                    {"key": "check_out", "label": "Check-out date?", "type": "date", "required": True},
                    {"key": "guests", "label": "Guests?", "type": "number", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
        ],
    },
    {
        "name": "Food",
        "icon": "🍔",
        "companies": [
            {
                "name": "DoorDash",
                "icon": "🔴",
                "form_schema": [
                    {"key": "order_id", "label": "Order ID (if any):", "type": "text", "required": False},
                    {"key": "restaurant", "label": "Restaurant name?", "type": "text", "required": False},
                    {"key": "issue_type", "label": "Issue type?", "type": "choice", "options": ["Missing item", "Wrong order", "Late delivery", "Refund", "Other"], "required": True},
                    {"key": "issue", "label": "Describe the issue:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Uber Eats",
                "icon": "🟢",
                "form_schema": [
                    {"key": "order_id", "label": "Order ID (if any):", "type": "text", "required": False},
                    {"key": "issue_type", "label": "Issue type?", "type": "choice", "options": ["Missing item", "Wrong order", "Late delivery", "Refund", "Other"], "required": True},
                    {"key": "issue", "label": "Describe the issue:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Grubhub",
                "icon": "🟠",
                "form_schema": [
                    {"key": "order_id", "label": "Order ID:", "type": "text", "required": False},
                    {"key": "issue", "label": "Describe the issue:", "type": "text", "required": True},
                ],
            },
        ],
    },
    {
        "name": "Tickets",
        "icon": "🎫",
        "companies": [
            {
                "name": "Ticketmaster",
                "icon": "🎵",
                "form_schema": [
                    {"key": "event_name", "label": "Event name?", "type": "text", "required": True},
                    {"key": "event_date", "label": "Event date?", "type": "date", "required": True},
                    {"key": "venue", "label": "Venue/City?", "type": "text", "required": True},
                    {"key": "num_tickets", "label": "Number of tickets?", "type": "number", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "StubHub",
                "icon": "🎟️",
                "form_schema": [
                    {"key": "event_name", "label": "Event name?", "type": "text", "required": True},
                    {"key": "event_date", "label": "Event date?", "type": "date", "required": True},
                    {"key": "num_tickets", "label": "Number of tickets?", "type": "number", "required": True},
                    {"key": "budget", "label": "Budget per ticket?", "type": "text", "required": False},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
        ],
    },
    {
        "name": "Movies",
        "icon": "🎬",
        "companies": [
            {
                "name": "AMC Theatres",
                "icon": "🍿",
                "form_schema": [
                    {"key": "movie_name", "label": "Movie name?", "type": "text", "required": True},
                    {"key": "location", "label": "Preferred theatre location?", "type": "text", "required": True},
                    {"key": "date", "label": "Date?", "type": "date", "required": True},
                    {"key": "num_tickets", "label": "Number of tickets?", "type": "number", "required": True},
                    {"key": "format", "label": "Format?", "type": "choice", "options": ["Standard", "IMAX", "Dolby", "3D"], "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Regal Cinemas",
                "icon": "👑",
                "form_schema": [
                    {"key": "movie_name", "label": "Movie name?", "type": "text", "required": True},
                    {"key": "location", "label": "Location?", "type": "text", "required": True},
                    {"key": "date", "label": "Date?", "type": "date", "required": True},
                    {"key": "num_tickets", "label": "Tickets?", "type": "number", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
        ],
    },
    {
        "name": "Shopping",
        "icon": "🛍️",
        "companies": [
            {
                "name": "Amazon",
                "icon": "📦",
                "form_schema": [
                    {"key": "order_id", "label": "Order ID:", "type": "text", "required": False},
                    {"key": "product", "label": "Product name/description:", "type": "text", "required": True},
                    {"key": "issue_type", "label": "Issue type?", "type": "choice", "options": ["Return", "Refund", "Not delivered", "Damaged", "Wrong item", "Other"], "required": True},
                    {"key": "issue", "label": "Describe the issue:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Walmart",
                "icon": "🔵",
                "form_schema": [
                    {"key": "order_id", "label": "Order ID:", "type": "text", "required": False},
                    {"key": "issue_type", "label": "Issue type?", "type": "choice", "options": ["Return", "Refund", "Not delivered", "Damaged", "Other"], "required": True},
                    {"key": "issue", "label": "Describe the issue:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Target",
                "icon": "🎯",
                "form_schema": [
                    {"key": "order_id", "label": "Order ID:", "type": "text", "required": False},
                    {"key": "issue", "label": "Describe the issue:", "type": "text", "required": True},
                ],
            },
        ],
    },
    {
        "name": "Rentals",
        "icon": "🚗",
        "companies": [
            {
                "name": "Hertz",
                "icon": "🟡",
                "form_schema": [
                    {"key": "pickup_location", "label": "Pickup location?", "type": "text", "required": True},
                    {"key": "pickup_date", "label": "Pickup date?", "type": "date", "required": True},
                    {"key": "return_date", "label": "Return date?", "type": "date", "required": True},
                    {"key": "car_type", "label": "Car type?", "type": "choice", "options": ["Economy", "Compact", "Midsize", "SUV", "Luxury"], "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Enterprise",
                "icon": "🟢",
                "form_schema": [
                    {"key": "pickup_location", "label": "Pickup location?", "type": "text", "required": True},
                    {"key": "pickup_date", "label": "Pickup date?", "type": "date", "required": True},
                    {"key": "return_date", "label": "Return date?", "type": "date", "required": True},
                    {"key": "car_type", "label": "Car type?", "type": "choice", "options": ["Economy", "Compact", "Midsize", "SUV", "Truck"], "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Turo",
                "icon": "🚙",
                "form_schema": [
                    {"key": "location", "label": "Location?", "type": "text", "required": True},
                    {"key": "dates", "label": "Rental dates?", "type": "text", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
        ],
    },
    {
        "name": "Rides",
        "icon": "🚕",
        "companies": [
            {
                "name": "Uber",
                "icon": "⬛",
                "form_schema": [
                    {"key": "trip_id", "label": "Trip ID (if any):", "type": "text", "required": False},
                    {"key": "issue_type", "label": "Issue type?", "type": "choice", "options": ["Overcharged", "Lost item", "Driver issue", "Safety concern", "Refund", "Other"], "required": True},
                    {"key": "issue", "label": "Describe the issue:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Lyft",
                "icon": "🩷",
                "form_schema": [
                    {"key": "ride_id", "label": "Ride ID (if any):", "type": "text", "required": False},
                    {"key": "issue_type", "label": "Issue type?", "type": "choice", "options": ["Overcharged", "Lost item", "Driver issue", "Safety concern", "Refund", "Other"], "required": True},
                    {"key": "issue", "label": "Describe the issue:", "type": "text", "required": True},
                ],
            },
        ],
    },
    {
        "name": "Bill Payments",
        "icon": "💳",
        "companies": [
            {
                "name": "Electric Bill",
                "icon": "⚡",
                "form_schema": [
                    {"key": "provider", "label": "Electric provider name?", "type": "text", "required": True},
                    {"key": "account_number", "label": "Account number:", "type": "text", "required": True},
                    {"key": "amount", "label": "Bill amount?", "type": "text", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Internet Bill",
                "icon": "🌐",
                "form_schema": [
                    {"key": "provider", "label": "Internet provider?", "type": "text", "required": True},
                    {"key": "account_number", "label": "Account number:", "type": "text", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Phone Bill",
                "icon": "📱",
                "form_schema": [
                    {"key": "carrier", "label": "Phone carrier?", "type": "text", "required": True},
                    {"key": "phone_number", "label": "Phone number on account:", "type": "text", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
            {
                "name": "Water Bill",
                "icon": "💧",
                "form_schema": [
                    {"key": "provider", "label": "Water provider?", "type": "text", "required": True},
                    {"key": "account_number", "label": "Account number:", "type": "text", "required": True},
                    {"key": "issue", "label": "Describe your request:", "type": "text", "required": True},
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with services and companies"

    def handle(self, *args, **options):
        for order, svc_data in enumerate(SERVICES_DATA):
            service, created = Service.objects.update_or_create(
                name=svc_data["name"],
                defaults={
                    "icon": svc_data["icon"],
                    "display_order": order,
                    "is_active": True,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} service: {service}")

            for c_order, comp_data in enumerate(svc_data["companies"]):
                company, c_created = Company.objects.update_or_create(
                    service=service,
                    name=comp_data["name"],
                    defaults={
                        "icon": comp_data["icon"],
                        "display_order": c_order,
                        "is_active": True,
                        "form_schema": comp_data["form_schema"],
                    },
                )
                c_action = "Created" if c_created else "Updated"
                self.stdout.write(f"    {c_action} company: {company}")

        self.stdout.write(self.style.SUCCESS(f"\nSeeded {len(SERVICES_DATA)} services successfully!"))
