# Stock Management System - Implementation Guide

## Overview
The stock management system has been completely refactored to properly track factory and showroom inventory with full audit trails. 

## Key Changes Made

### 1. **New Database Models**

#### FactoryStock
- Tracks the global inventory at the factory for each product
- Single entry per product
- Updated when showrooms receive or return products
- **Formula**: Decreases on receive, increases on return

#### ShowroomStock
- Tracks current inventory for each showroom-product combination
- Updated immediately when stock is received, sold, or returned
- Prevents overselling by validating against this quantity
- **Formula**: Increases on receive, decreases on sale/return

#### StockTransfer
- Complete audit trail of all inventory movements
- Records: date, product, quantity, transfer type (receive/sale/return), user, timestamp
- Used for reporting and reconciliation
- Never modified or deleted (immutable log)

### 2. **New API Endpoints**

#### Factory Stock (Admin Only)
```
GET /api/inventory/factory-stocks/
- View global factory inventory
- Shows quantity available for showrooms to receive
```

#### Showroom Stock (Admin can view all, Showrooms see their own)
```
GET /api/inventory/showroom-stocks/
- View current inventory for each showroom
- Prevents overselling by validating available quantity
```

#### Stock Transfers (Core Operations)
```
POST /api/inventory/transfers/
- Create stock transfers (receive, sale, return)
- Automatically validates available inventory
- Updates factory and showroom stocks
- Creates immutable audit trail

GET /api/inventory/transfers/
- View all stock movements
- Filter by date, product, transfer type, showroom
- Complete history for reporting

GET /api/inventory/transfers/summary/
- Quick summary: total received, sold, returned
- Grouped by product
```

### 3. **Stock Transfer Types**

#### RECEIVE (Factory → Showroom)
```json
{
  "transfer_type": "receive",
  "product": <product_id>,
  "quantity": <number>,
  "date": "2024-01-15"
}
```
- Decreases factory stock
- Increases showroom stock
- Validation: Factory must have enough units

#### SALE (Showroom → Customer)
```json
{
  "transfer_type": "sale",
  "product": <product_id>,
  "quantity": <number>,
  "date": "2024-01-15"
}
```
- Decreases showroom stock only
- Validation: Showroom must have enough units

#### RETURN (Showroom → Factory)
```json
{
  "transfer_type": "return",
  "product": <product_id>,
  "quantity": <number>,
  "date": "2024-01-15"
}
```
- Decreases showroom stock
- Increases factory stock
- Validation: Showroom must have enough units to return

### 4. **Validation & Business Logic**

✅ **Automatic Validations:**
- Cannot receive more than factory has
- Cannot sell more than showroom has
- Cannot return more than showroom has
- All quantities must be positive integers

✅ **Data Integrity:**
- All operations use database transactions
- Inventory updates are atomic
- Audit trail is immutable

### 5. **Frontend Changes**

The Stock Entry page has been completely redesigned:

**Old System:**
- Used daily stock entries with opening/received/sold/return quantities
- Sent data as strings causing type errors
- No validation before submission

**New System:**
- Separate buttons for Receive/Sale/Return operations
- Proper integer conversion before sending
- Real-time stock display shows current available quantity
- Clear visual feedback on transfer types
- Auto-scoped to user's showroom (security)

## How to Use

### For Showroom Users

**Receive Products from Factory:**
1. Go to "Stock Management"
2. Select "Receive from Factory" from the dropdown
3. Choose the product
4. Enter the quantity
5. Click "Record Receive"
6. Stock is instantly available in their inventory

**Sell Products to Customers:**
1. Select "Sale to Customer" from the dropdown
2. Choose the product
3. Enter the quantity (system shows available stock)
4. Click "Record Sale"
5. Stock is automatically deducted

**Return Products to Factory:**
1. Select "Return to Factory" from the dropdown
2. Choose the product
3. Enter the quantity to return
4. Click "Record Return"
5. Stock is deducted from showroom and added to factory

### For Admins

**View Factory Inventory:**
```
GET /api/inventory/factory-stocks/
```
- See total units available for each product
- Plan shipments to showrooms

**View All Showroom Inventory:**
```
GET /api/inventory/showroom-stocks/?showroom=<id>
```
- Monitor each showroom's current stock
- Identify low-stock situations

**Generate Reports:**
```
GET /api/inventory/transfers/summary/?date_from=2024-01-01&date_to=2024-01-31
```
- Total products received by each showroom
- Total products sold by each showroom
- Total products returned

**Create Transfers for Showroom:**
```
POST /api/inventory/transfers/
- Pass showroom_id explicitly
- Creates transfer on behalf of showroom
```

## Testing

Three test scripts are included:

1. **test_login.py** - Verify user authentication
2. **init_factory_stock.py** - Initialize factory stock for products
3. **test_stock_management.py** - Verify all stock operations work

Run tests:
```bash
python test_login.py
python init_factory_stock.py
python test_stock_management.py
```

## Database Queries

### Check Factory Stock
```sql
SELECT product_id, product.name, factory_stock.quantity 
FROM inventory_factorystock
LEFT JOIN products_product ON product_id = products_product.id;
```

### Check Showroom Stock
```sql
SELECT showroom.name, product.name, showroom_stock.quantity
FROM inventory_showroomstock
LEFT JOIN showrooms_showroom ON showroom_id = showrooms_showroom.id
LEFT JOIN products_product ON product_id = products_product.id
WHERE showroom_id = <id>;
```

### View Stock Transfers
```sql
SELECT date, transfer_type, product.name, quantity
FROM inventory_stocktransfer
LEFT JOIN products_product ON product_id = products_product.id
WHERE showroom_id = <id>
ORDER BY date DESC, created_at DESC;
```

## Error Handling

The API returns clear error messages:

```json
{
  "non_field_errors": [
    "Cannot sell 50 units. Showroom only has 30 units in stock."
  ]
}
```

Frontend displays these directly to the user.

## API Response Examples

### List Showroom Stocks
```json
[
  {
    "id": 1,
    "showroom": 1,
    "showroom_name": "Mahadi Zone",
    "product": 5,
    "product_name": "Premium Panjabi",
    "quantity": 45,
    "updated_at": "2024-01-15T14:30:00Z"
  }
]
```

### Create Transfer
```json
{
  "id": 124,
  "showroom": 1,
  "showroom_name": "Mahadi Zone",
  "product": 5,
  "product_name": "Premium Panjabi",
  "transfer_type": "receive",
  "quantity": 25,
  "date": "2024-01-15",
  "notes": "",
  "created_by": 2,
  "created_by_username": "admin",
  "created_at": "2024-01-15T14:32:15Z"
}
```

### Transfer Summary
```json
{
  "received": 100,
  "sold": 65,
  "returned": 10,
  "by_product": {
    "5_Premium Panjabi": {
      "received": 100,
      "sold": 65,
      "returned": 10
    }
  }
}
```

## Migration Notes

The system maintains backward compatibility:
- Existing `DailyStock` and `DailyBalance` models still work
- Can run both systems in parallel if needed
- All old data is preserved
- New stock management runs independently

## Summary of Validation

| Operation | Validation |
|-----------|-----------|
| Receive | Factory quantity >= requested |
| Sale | Showroom quantity >= requested |
| Return | Showroom quantity >= requested |
| All | Quantity > 0, integers only |

## Security

- Showroom users auto-scoped to their own inventory
- Admin can see all showrooms or filter to specific one
- All changes tracked with user attribution
- Immutable audit trail cannot be modified
- Database constraints prevent negative stock
