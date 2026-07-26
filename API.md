# Wiwi Events REST API Documentation (v1)

The **Wiwi Events REST API** provides endpoints for managing events, registering for events, and user token authentication.

---

## Authentication

The API supports both **Session Authentication** (for browser testing via `/api/v1/`) and **Token Authentication** (via `Authorization: Token <your_token>` header).

### Obtain Auth Token
- **POST** `/api/v1/auth/token/`
- **Auth Required:** None
- **Request Body:**
```json
{
  "username": "sneha",
  "password": "yourpassword"
}
```
- **Response (200 OK):**
```json
{
  "token": "9944b09199c62bcf9418ad846d0e4e2c6ac63d0c"
}
```

---

## Endpoints Summary

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/events/` | List all visible events (approved, or own unapproved) | Optional |
| `POST` | `/api/v1/events/` | Submit a new event for admin approval | **Required** |
| `GET` | `/api/v1/events/{id}/` | Retrieve detailed event info | Optional |
| `PUT` / `PATCH` | `/api/v1/events/{id}/` | Update an event (Organizer or Staff only) | **Required** |
| `DELETE` | `/api/v1/events/{id}/` | Delete an event (Organizer or Staff only) | **Required** |
| `GET` | `/api/v1/registrations/` | List user's event registrations | **Required** |
| `POST` | `/api/v1/registrations/` | Register for an event | **Required** |
| `DELETE` | `/api/v1/registrations/{id}/` | Cancel a registration (Owner or Staff only) | **Required** |

---

## Endpoint Details

### 1. List & Search Events
- **GET** `/api/v1/events/`
- **Query Parameters:**
  - `category`: Filter by category (e.g. `WORKSHOP`, `CONFERENCE`, `MEETUP`, `HACKATHON`, `WEBINAR`, `OTHER`)
  - `event_type`: Filter by format (`IN_PERSON`, `VIRTUAL`, `HYBRID`)
  - `upcoming`: Set to `true` to filter events scheduled in the future (`date__gte=now`)
  - `search`: Search across title, description, location, and speaker name
  - `page`: Page number (default page size: 10)
- **Response (200 OK):**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "AI & Full-Stack Tech Summit 2026",
      "description": "Annual flagship gathering of engineers and AI researchers.",
      "location": "Convention Center & Online",
      "date": "2026-08-15T10:00:00Z",
      "capacity": 200,
      "category": "CONFERENCE",
      "event_type": "HYBRID",
      "speaker_name": "Dr. Sarah Jenkins",
      "speaker_role": "Head of AI Research",
      "image": "/media/event_banners/summit.jpg",
      "is_approved": true,
      "organizer": 1,
      "organizer_username": "SNEHA",
      "slots_left": 198,
      "created_at": "2026-07-26T10:00:00Z"
    }
  ]
}
```

### 2. Create Event
- **POST** `/api/v1/events/`
- **Auth Required:** Token or Session
- **Request Body:**
```json
{
  "title": "Python & Django Masterclass",
  "description": "Hands-on deep dive into building scalable web APIs.",
  "location": "Tech Hub Room A",
  "date": "2026-09-01T14:00:00Z",
  "capacity": 50,
  "category": "WORKSHOP",
  "event_type": "IN_PERSON",
  "speaker_name": "Alex Rivera",
  "speaker_role": "Lead Architect"
}
```
- **Response (201 Created):**
```json
{
  "id": 2,
  "title": "Python & Django Masterclass",
  "description": "Hands-on deep dive into building scalable web APIs.",
  "location": "Tech Hub Room A",
  "date": "2026-09-01T14:00:00Z",
  "capacity": 50,
  "category": "WORKSHOP",
  "event_type": "IN_PERSON",
  "speaker_name": "Alex Rivera",
  "speaker_role": "Lead Architect",
  "image": null,
  "slots_left": 50,
  "created_at": "2026-07-26T18:00:00Z"
}
```
*Note: Newly submitted events default to `is_approved=False` until approved by an admin.*

---

### 3. Register for an Event
- **POST** `/api/v1/registrations/`
- **Auth Required:** Token or Session
- **Request Body:**
```json
{
  "event": 1
}
```
- **Response (201 Created):**
```json
{
  "id": 15,
  "user": 2,
  "user_username": "JOHN_DOE",
  "event": 1,
  "event_title": "AI & Full-Stack Tech Summit 2026",
  "ticket_code": "TIC-4F8A2E19",
  "registered_at": "2026-07-26T18:10:00Z"
}
```
- **Error Response (400 Bad Request - Capacity / Double Booking):**
```json
{
  "detail": "Event is fully booked!"
}
```

---

## Example `curl` Commands

### 1. Get Auth Token
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username": "sneha", "password": "yourpassword"}'
```

### 2. List Approved Events (Filter & Search)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/events/?upcoming=true&search=Python"
```

### 3. Create Event (Authenticated)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/events/ \
     -H "Authorization: Token YOUR_AUTH_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
           "title": "Cloud Native Meetup",
           "description": "Kubernetes and Docker best practices.",
           "location": "Online Zoom",
           "date": "2026-09-10T18:00:00Z",
           "capacity": 100,
           "category": "MEETUP",
           "event_type": "VIRTUAL"
         }'
```

### 4. Register for Event (Authenticated & Capacity Protected)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/registrations/ \
     -H "Authorization: Token YOUR_AUTH_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"event": 1}'
```

### 5. Cancel Registration
```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/registrations/15/ \
     -H "Authorization: Token YOUR_AUTH_TOKEN"
```
