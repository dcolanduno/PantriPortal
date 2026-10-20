# PANTRY PORTAL - DROP 4A SPECIFICATION

## Product

Pantry Portal

## Milestone

DROP 4A - SHOPPING LISTS, REPLENISHMENT & INVENTORY AUTOMATION

This drop extends:

- Drop 1 Authentication Foundation
- Drop 2 Inventory Foundation
- Drop 3 Barcode Recognition & Product Catalog

Do NOT modify existing behavior except where necessary to support this drop.

All existing tests must continue to pass.

---

# OBJECTIVE

Allow users to:

- Create Shopping Lists
- Create Shopping List Templates
- Add Products To Shopping Lists
- Generate Shopping Lists Automatically
- Create Replenishment Rules
- Detect Low Inventory
- Generate Smart Shopping Recommendations
- Mark Items Purchased
- Mark Items Unavailable
- Synchronize Purchased Items Back Into Inventory
- Build Dashboard Widgets For Shopping Activities

---

# BUSINESS RULES

Pantry Portal should automatically identify:

- Low stock items
- Out-of-stock items
- Frequently purchased items
- Auto-replenish products

Examples:

```text
Milk

Current Quantity: 1

Minimum Quantity: 2

Preferred Quantity: 4

Suggested Purchase Quantity: 3
```

---

# DOMAIN OBJECTS

---

# SHOPPING LIST

```csharp
public class ShoppingList
{
    public Guid Id { get; set; }

    public Guid UserId { get; set; }

    public string Name { get; set; }

    public bool IsArchived { get; set; }

    public DateTime CreatedDate { get; set; }

    public DateTime UpdatedDate { get; set; }
}
```

---

# SHOPPING LIST ITEM

```csharp
public class ShoppingListItem
{
    public Guid Id { get; set; }

    public Guid ShoppingListId { get; set; }

    public Guid ProductId { get; set; }

    public decimal QuantityRequested { get; set; }

    public string Unit { get; set; }

    public bool Purchased { get; set; }

    public bool Unavailable { get; set; }

    public DateTime CreatedDate { get; set; }

    public DateTime UpdatedDate { get; set; }
}
```

---

# SHOPPING LIST TEMPLATE

```csharp
public class ShoppingListTemplate
{
    public Guid Id { get; set; }

    public Guid UserId { get; set; }

    public string Name { get; set; }

    public DateTime CreatedDate { get; set; }
}
```

---

# SHOPPING LIST TEMPLATE ITEM

```csharp
public class ShoppingListTemplateItem
{
    public Guid Id { get; set; }

    public Guid ShoppingListTemplateId { get; set; }

    public Guid ProductId { get; set; }

    public decimal Quantity { get; set; }

    public string Unit { get; set; }
}
```

---

# INVENTORY REPLENISHMENT RULE

```csharp
public class InventoryReplenishmentRule
{
    public Guid Id { get; set; }

    public Guid InventoryItemId { get; set; }

    public decimal MinimumQuantity { get; set; }

    public decimal PreferredQuantity { get; set; }

    public bool AutoReplenish { get; set; }

    public bool AutoAddToShoppingList { get; set; }
}
```

---

# DATABASE TABLES

Create:

```text
ShoppingLists

ShoppingListItems

ShoppingListTemplates

ShoppingListTemplateItems

InventoryReplenishmentRules
```

Generate migrations.

---

# INDEXES

Create indexes on:

```text
ShoppingLists.UserId

ShoppingLists.IsArchived

ShoppingListItems.ProductId

ShoppingListItems.Purchased

InventoryReplenishmentRules.InventoryItemId
```

---

# REPOSITORIES

Generate:

```text
IShoppingListRepository

IShoppingListItemRepository

ITemplateRepository

IReplenishmentRuleRepository
```

Implement EF Core repositories.

---

# SERVICES

Generate:

```text
ShoppingListService

ShoppingListTemplateService

InventoryAutomationService

ReplenishmentService

DashboardShoppingService
```

All async.

---

# AUTO REPLENISHMENT LOGIC

If:

```text
Current Quantity <= Minimum Quantity
```

AND

```text
AutoReplenish == true
```

Then:

```text
Required Quantity =
Preferred Quantity - Current Quantity
```

Create shopping list entry automatically.

---

# DUPLICATE PREVENTION

Shopping list must never contain duplicate products.

If an item exists already:

```text
Increase QuantityRequested
```

instead of creating another row.

---

# SHOPPING LIST STATUS

Calculate:

```text
Pending

Completed

Archived
```

Do not store.

Calculated dynamically.

---

# CONTROLLERS

Generate:

```text
ShoppingListsController

ShoppingTemplatesController

InventoryAutomationController

DashboardController
```

---

# SHOPPING LIST API

Route:

```text
/api/shopping-lists
```

---

# CREATE LIST

POST

```text
/api/shopping-lists
```

---

# GET LISTS

GET

```text
/api/shopping-lists
```

Filters:

```text
active=true

archived=true
```

---

# GET LIST BY ID

GET

```text
/api/shopping-lists/{id}
```

---

# UPDATE LIST

PUT

```text
/api/shopping-lists/{id}
```

---

# DELETE LIST

DELETE

```text
/api/shopping-lists/{id}
```

---

# ARCHIVE LIST

POST

```text
/api/shopping-lists/{id}/archive
```

---

# SHOPPING LIST ITEMS

---

# ADD ITEM

POST

```text
/api/shopping-lists/{id}/items
```

Request

```json
{
  "productId":"guid",
  "quantity":2,
  "unit":"Boxes"
}
```

---

# UPDATE ITEM

PUT

```text
/api/shopping-lists/items/{id}
```

---

# REMOVE ITEM

DELETE

```text
/api/shopping-lists/items/{id}
```

---

# MARK PURCHASED

POST

```text
/api/shopping-lists/items/{id}/purchased
```

---

# MARK UNAVAILABLE

POST

```text
/api/shopping-lists/items/{id}/unavailable
```

---

# BULK PURCHASED

POST

```text
/api/shopping-lists/bulk-purchased
```

Request

```json
{
  "itemIds":[]
}
```

---

# TEMPLATE SYSTEM

---

# CREATE TEMPLATE

POST

```text
/api/shopping-templates
```

---

# CREATE TEMPLATE FROM LIST

POST

```text
/api/shopping-templates/from-list/{shoppingListId}
```

---

# CREATE LIST FROM TEMPLATE

POST

```text
/api/shopping-templates/{id}/create-shopping-list
```

---

# LOW STOCK ENGINE

Generate:

```text
InventoryAutomationService
```

---

# LOW STOCK DETECTION

Criteria:

```text
CurrentQuantity <= MinimumQuantity
```

---

# LOW STOCK REPORT

GET

```text
/api/automation/low-stock
```

Returns:

```json
[
  {
    "product":"Milk",
    "currentQuantity":1,
    "minimumQuantity":2,
    "preferredQuantity":4
  }
]
```

---

# OUT OF STOCK REPORT

GET

```text
/api/automation/out-of-stock
```

---

# AUTO GENERATE SHOPPING LIST

POST

```text
/api/automation/generate-list
```

Behavior:

```text
Create Shopping List

Add Low Stock Products

Avoid Duplicates

Return List
```

---

# REPLENISHMENT RULES

Generate endpoint.

PUT

```text
/api/inventory/{inventoryItemId}/replenishment
```

Request

```json
{
  "minimumQuantity":2,
  "preferredQuantity":5,
  "autoReplenish":true,
  "autoAddToShoppingList":true
}
```

---

# PURCHASE WORKFLOW

Create endpoint.

POST

```text
/api/shopping-lists/items/{id}/add-to-inventory
```

Request

```json
{
  "storageLocationId":"guid",
  "quantity":2
}
```

Behavior:

```text
Update Inventory

Increase Quantity

Mark Purchased
```

---

# DASHBOARD

Extend Dashboard Service.

---

# DASHBOARD RESPONSE

```json
{
  "shoppingListCount":3,

  "pendingShoppingItems":22,

  "lowStockItems":9,

  "outOfStockItems":2,

  "autoReplenishmentItems":14
}
```

---

# AUTOMATION HOSTED SERVICE

Generate:

```text
LowStockMonitorHostedService
```

Runs:

```text
Every Hour
```

Responsibilities:

```text
Scan Inventory

Apply Rules

Generate Recommendations

Update Dashboard Cache
```

---

# CACHING

Use:

```text
IMemoryCache
```

Cache:

```text
Shopping Dashboard

Low Stock Reports

Shopping Metrics
```

Expiration:

```text
15 Minutes
```

---

# REPORTING

Generate report endpoints.

---

# SHOPPING REPORT

GET

```text
/api/reports/shopping
```

Contains:

```text
Items Purchased

Items Unavailable

Most Purchased Products

Shopping Activity
```

---

# REPLENISHMENT REPORT

GET

```text
/api/reports/replenishment
```

Contains:

```text
Low Stock Trends

Products Frequently Replenished

Replenishment Activity
```

---

# SWAGGER

Add examples for:

```text
Shopping Lists

Templates

Low Stock

Generated Lists

Purchased Workflow

Replenishment Rules
```

---

# TESTING

Create:

```text
Unit Tests

Integration Tests
```

---

# UNIT TESTS

Coverage:

```text
ShoppingListService

TemplateService

InventoryAutomationService

ReplenishmentService

DashboardShoppingService
```

---

# INTEGRATION TESTS

Coverage:

```text
Create List

Add Item

Archive List

Create Template

Generate List

Low Stock Detection

Add Purchased Item To Inventory

Duplicate Prevention
```

---

# PERFORMANCE

Support:

```text
10,000 Inventory Items

100 Shopping Lists

1,000 Shopping List Items
```

Generation target:

```text
< 2 seconds
```

---

# SECURITY

All endpoints require authentication.

Owner

Administrator

Member

Can modify lists.

Viewer

Read Only.

---

# README

Add sections:

```text
Shopping Lists

Shopping Templates

Low Stock Monitoring

Auto Replenishment

Add Purchased To Inventory

Reports

Dashboard
```

---

# SUCCESS CRITERIA

The implementation is complete when:

```bash
dotnet restore
```

passes.

```bash
dotnet build
```

passes.

```bash
dotnet test
```

passes.

All previous drops continue functioning.

Shopping Lists function.

Templates function.

Low Stock Detection functions.

Replenishment Rules function.

Purchased Items update Inventory.

Hosted Service functions.

Dashboard updated successfully.

Swagger fully documents all new endpoints.

---

# FINAL AGENT INSTRUCTION

Implement every requirement completely.

Do not stop after scaffolding.

Generate:

- Entities
- Migrations
- DTOs
- Repositories
- Services
- Controllers
- Background Services
- Dashboard Extensions
- Reports
- Unit Tests
- Integration Tests
- Swagger Documentation

Continue until:

- Solution Compiles
- Tests Pass
- Shopping Automation Functions
- Replenishment Functions
- Dashboard Functions

Commit all changes with:

feat(drop4a): implement shopping lists and replenishment automation

Then stop and wait for Drop 4B Expiration Tracking, Notifications and Inventory Transactions.