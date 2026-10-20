# PANTRY PORTAL - DROP 4B SPECIFICATION

## Product

Pantry Portal

## Milestone

DROP 4B - EXPIRATION TRACKING, NOTIFICATIONS, INVENTORY TRANSACTIONS & AUDIT HISTORY

This drop extends:

- Drop 1 Authentication Foundation
- Drop 2 Inventory Foundation
- Drop 3 Barcode Recognition & Product Catalog
- Drop 4A Shopping Lists & Replenishment

Do NOT break any existing functionality.

All previous tests must continue passing.

All APIs must remain backward compatible.

---

# OBJECTIVE

Implement a complete inventory lifecycle management system.

Users must be able to:

- Track product expiration dates
- View upcoming expirations
- View expired items
- Receive expiration notifications
- Track all inventory changes
- Audit inventory history
- Track food waste
- Track consumption
- Track manual adjustments
- Track purchases
- Review inventory timelines
- Generate expiration reports
- Generate waste reports

This creates the foundation for:

- Analytics
- Forecasting
- Pantry Health Score
- AI Recommendations

in future releases.

---

# HIGH LEVEL ARCHITECTURE

Every inventory change must be recorded.

Inventory should become fully auditable.

Example:

```text
Milk

Created
+2

Consumed
-1

Consumed
-1

Expired
-0.5

Adjusted
+1
```

Complete history remains available.

---

# DOMAIN ENTITIES

---

# INVENTORY TRANSACTION

```csharp
public class InventoryTransaction
{
    public Guid Id { get; set; }

    public Guid InventoryItemId { get; set; }

    public Guid UserId { get; set; }

    public InventoryTransactionType TransactionType { get; set; }

    public decimal QuantityChange { get; set; }

    public decimal QuantityBefore { get; set; }

    public decimal QuantityAfter { get; set; }

    public string? Notes { get; set; }

    public DateTime CreatedDate { get; set; }
}
```

---

# INVENTORY TRANSACTION TYPE

```csharp
public enum InventoryTransactionType
{
    Added = 1,

    Consumed = 2,

    Purchased = 3,

    Expired = 4,

    Adjusted = 5,

    Removed = 6,

    Imported = 7
}
```

---

# EXPIRATION NOTIFICATION

```csharp
public class ExpirationNotification
{
    public Guid Id { get; set; }

    public Guid InventoryItemId { get; set; }

    public int DaysBeforeExpiration { get; set; }

    public DateTime ScheduledDate { get; set; }

    public bool Sent { get; set; }

    public DateTime? SentDate { get; set; }
}
```

---

# USER NOTIFICATION

```csharp
public class UserNotification
{
    public Guid Id { get; set; }

    public Guid UserId { get; set; }

    public string NotificationType { get; set; }

    public string Title { get; set; }

    public string Message { get; set; }

    public bool Read { get; set; }

    public DateTime CreatedDate { get; set; }
}
```

---

# FOOD WASTE EVENT

```csharp
public class FoodWasteEvent
{
    public Guid Id { get; set; }

    public Guid InventoryItemId { get; set; }

    public Guid ProductId { get; set; }

    public decimal QuantityWasted { get; set; }

    public string Unit { get; set; }

    public string Reason { get; set; }

    public DateTime WastedDate { get; set; }
}
```

---

# DATABASE TABLES

Generate migrations.

Create:

```text
InventoryTransactions

ExpirationNotifications

UserNotifications

FoodWasteEvents
```

---

# INDEXES

Create indexes for:

```text
InventoryItemId

TransactionType

CreatedDate

ScheduledDate

Sent

UserId

WastedDate
```

---

# INVENTORY TRANSACTION ENGINE

Every inventory modification must generate transactions.

Examples:

---

# ADD INVENTORY

```text
Inventory Created

Quantity: +5
```

Creates:

```text
Transaction Type:
Added
```

---

# CONSUME INVENTORY

```text
Consume 2 Eggs
```

Creates:

```text
Consumed
```

Transaction.

---

# MANUAL ADJUSTMENT

```text
Quantity 5 → 7
```

Creates:

```text
Adjusted
```

Transaction.

---

# PURCHASE WORKFLOW

From Shopping Lists.

Creates:

```text
Purchased
```

Transaction.

---

# EXPIRED PRODUCT

Creates:

```text
Expired
```

Transaction.

Creates:

```text
FoodWasteEvent
```

---

# EXPIRATION MANAGEMENT

Every inventory item with expiration date must be monitored.

---

# EXPIRATION RULES

Default schedule:

```text
30 Days Before

14 Days Before

7 Days Before

3 Days Before

1 Day Before

Day Of Expiration
```

Generate notifications automatically.

---

# EXPIRATION SERVICE

Generate:

```text
ExpirationMonitoringService
```

Responsibilities:

```text
Find Expiring Items

Create Notifications

Mark Expired Items

Create Waste Records

Generate Reports
```

---

# NOTIFICATION SERVICE

Generate:

```text
NotificationService
```

Responsibilities:

```text
Create Notifications

Mark Read

Get Unread Counts

Get User Notifications
```

---

# NOTIFICATION TYPES

Supported:

```text
LowStock

ExpiringSoon

Expired

InventoryAdjusted

PurchaseCompleted

ShoppingListGenerated
```

---

# NOTIFICATION CONTROLLER

Route:

```text
/api/notifications
```

---

# GET NOTIFICATIONS

GET

```text
/api/notifications
```

---

# GET UNREAD

GET

```text
/api/notifications/unread
```

---

# MARK READ

POST

```text
/api/notifications/{id}/read
```

---

# MARK ALL READ

POST

```text
/api/notifications/read-all
```

---

# EXPIRATION CONTROLLER

Route:

```text
/api/expiration
```

---

# EXPIRING ITEMS

GET

```text
/api/expiration/expiring
```

Query:

```text
days=7
```

Returns:

```json
[
  {
    "product":"Milk",
    "expirationDate":"2027-03-12",
    "daysRemaining":3
  }
]
```

---

# EXPIRED ITEMS

GET

```text
/api/expiration/expired
```

---

# EXPIRING TODAY

GET

```text
/api/expiration/today
```

---

# EXPIRING THIS WEEK

GET

```text
/api/expiration/this-week
```

---

# INVENTORY TRANSACTIONS CONTROLLER

Route:

```text
/api/inventory-transactions
```

---

# TRANSACTION HISTORY

GET

```text
/api/inventory-transactions
```

Filters:

```text
Inventory Item

Date Range

Transaction Type
```

---

# PRODUCT TIMELINE

GET

```text
/api/inventory-transactions/product/{productId}
```

Returns:

Complete inventory history.

---

# USER ACTIVITY

GET

```text
/api/inventory-transactions/user/{userId}
```

Returns:

Changes made by user.

---

# FOOD WASTE CONTROLLER

Route:

```text
/api/food-waste
```

---

# WASTE REPORT

GET

```text
/api/food-waste
```

---

# WASTE BY CATEGORY

GET

```text
/api/food-waste/by-category
```

---

# WASTE BY PRODUCT

GET

```text
/api/food-waste/by-product
```

---

# MANUAL WASTE ENTRY

POST

```text
/api/food-waste
```

Request:

```json
{
  "inventoryItemId":"guid",
  "quantity":1,
  "reason":"Spoiled"
}
```

---

# DASHBOARD EXTENSIONS

Extend existing dashboard.

Return:

```json
{
  "expiringItems":12,
  "expiredItems":4,
  "unreadNotifications":7,
  "foodWasteEvents":3,
  "inventoryTransactions":245
}
```

---

# BACKGROUND SERVICES

Generate:

```text
ExpirationMonitorHostedService
