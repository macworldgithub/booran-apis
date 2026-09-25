# Booran Motors Dealerships API

A NestJS + MongoDB REST API backend that parses, normalizes, and stores vehicle inventory data from 12 CSV files across 6 dealership stores, providing dedicated GET endpoints with `new` and `used` vehicle filters, search, and automated syncing.

---

## 🏬 Dealership Stores & Endpoints

| Store # | Dealership Name | Brand | Location | Dedicated Endpoint |
|---|---|---|---|---|
| **01** | Cheltenham Kia | Kia | Cheltenham | `/api/stores/cheltenham-kia` (or `/api/store01`) |
| **20** | Cranbourne Hyundai | Hyundai | Cranbourne | `/api/stores/cranbourne-hyundai` (or `/api/store20`) |
| **40** | South Morang Hyundai | Hyundai | South Morang | `/api/stores/south-morang-hyundai` (or `/api/store40`) |
| **50** | Dandenong Hyundai | Hyundai | Dandenong | `/api/stores/dandenong-hyundai` (or `/api/store50`) |
| **70** | South Morang Kia | Kia | South Morang | `/api/stores/south-morang-kia` (or `/api/store70`) |
| **90** | Berwick Hyundai | Hyundai | Berwick | `/api/stores/berwick-hyundai` (or `/api/store90`) |

### Summary & Overview Endpoint
- `GET /api/stores` - Returns list of all 6 stores with total, new, and used vehicle counts.

### Dynamic Store Endpoint
- `GET /api/stores/:identifier` - Accepts store ID (`store01`, `01`) or slug (`cheltenham-kia`).

### Global Search Endpoint
- `GET /api/vehicles` - Search across all stores.
- `GET /api/vehicles/:stockNumber` - Fetch details for a specific vehicle by stock number.

---

## 🔍 Query Parameters & Filtering

All store and vehicle endpoints support the following query parameters:

| Parameter | Type | Example | Description |
|---|---|---|---|
| `type` | `string` | `?type=new` or `?type=used` | Filter by vehicle category (new or used) |
| `status` | `string` | `?status=IN-STOCK` | Filter by stock status (`IN-STOCK`, `LOANER`, `WHOLESALE`, etc.) |
| `carline` | `string` | `?carline=CARNIVAL` | Filter by model/carline |
| `search` | `string` | `?search=GT-LINE` | Search across description, stock#, colour, regNo |
| `sort` | `string` | `?sort=listPrice` | Field to sort by (`listPrice`, `age`, `year`, `createdAt`) |
| `order` | `string` | `?order=asc` or `?order=desc` | Sort order |
| `limit` | `number` | `?limit=50` | Pagination limit |
| `page` | `number` | `?page=1` | Pagination page number |

### Examples:
```bash
# Get only NEW cars from Cheltenham Kia:
GET http://localhost:3000/api/stores/cheltenham-kia?type=new

# Get only USED cars from Cranbourne Hyundai:
GET http://localhost:3000/api/stores/cranbourne-hyundai?type=used

# Get IN-STOCK Sorento cars from South Morang Kia:
GET http://localhost:3000/api/stores/south-morang-kia?carline=SORENTO&status=IN-STOCK

# Search all stores for Carnival:
GET http://localhost:3000/api/vehicles?search=CARNIVAL
```

---

## 📖 Interactive Swagger API Documentation

Start the server and visit:
```
http://localhost:3000/api/docs
```
Interactive UI to test every endpoint, inspect schemas, and view real response payloads.

---

## 💾 CSV Ingestion & MongoDB Sync

All 1,739 vehicles from the 12 CSV files are stored in the MongoDB Atlas database:
- **Database**: `Booran_APIS`
- **Collection**: `vehicles` (compound unique index on `storeId` + `stockNumber`)

### Running the Seed Script Manually
```bash
npm run seed
```

### Sync via API Endpoint
```bash
POST http://localhost:3000/api/vehicles/sync
```

---

## 🚀 Running the Project

```bash
# Start Development Server (with auto-reload)
npm run start:dev

# Start Production Server
npm run start

# Build TypeScript
npm run build
```
