# Supplier Product & Stock Sync

This module synchronizes a daily JSON product feed from a supplier to Odoo, creating and updating products, categories, and stock quantities automatically. It also provides a webhook for real-time price updates.

## Installation
1. Place this module (`supplier_product_sync`) in your Odoo `addons` directory.
2. Update the app list in Odoo and install `Supplier Product & Stock Sync`.

## Configuration
1. Go to **Inventory > Configuration > Settings**.
2. Scroll to the **Supplier Sync** section.
3. Configure the **Supplier Feed Path** (local file path or URL) and **Webhook Token**.

## Usage
- The sync runs daily via a scheduled action (Cron job).
- You can manually trigger a sync from **Inventory > Configuration > Settings > Supplier Sync > Sync Logs** by clicking **Sync Now**.
- Webhook URL: `POST /api/supplier/price`
  Headers: `Authorization: Bearer <Webhook Token>`
  Payload: `{"sku": "TV-55-SAM", "price": 579.00}`

## Questions

### 1. How would your solution behave with 200,000 products instead of 20,000? What would you change?
With 200,000 products, reading the entire feed into memory and processing it might cause memory and timeout issues. The current implementation uses ORM `create()` and `write()` which could take a while for 200k records.
To handle 200k products, I would:
- Stream the JSON file using `ijson` instead of loading it entirely into memory.
- Process the records in smaller batches (e.g. 5,000 records) and commit each batch to avoid long-running transactions and memory exhaustion.
- Use direct PostgreSQL `INSERT ON CONFLICT DO UPDATE` or Odoo's `_load_records` method for much faster bulk inserts/updates bypassing ORM tracking.

### 2. What happens if the sync is started twice at the same time? How did you (or would you) prevent problems?
Running it twice at the same time might cause race conditions resulting in duplicate categories or products being created.
Currently, this could happen if a manual sync is clicked right as the cron job starts.
To prevent this, I would implement a locking mechanism. We could use Odoo's `_lock` functionality or simply add a `state` field on a singleton configuration record (e.g. `is_syncing`). Another approach is to use PostgreSQL advisory locks (`pg_try_advisory_xact_lock()`) to ensure only one sync process can run simultaneously for the feed.

### 3. If a product disappears from the supplier feed, what should happen to it in Odoo? What did you implement, and why?
In the current implementation, if a product disappears from the feed, it is simply ignored and remains in Odoo untouched. 
I chose this approach because a supplier feed might occasionally omit products temporarily (e.g. out of stock or catalog refresh). We do not want to delete a product that we may have sold in the past because it breaks historical data (sales, stock moves).
In a production scenario, we could archive the product (`active=False`), set its stock to 0, or flag it as "discontinued".

### 4. What would you add before putting this into production for a real client?
- Retry mechanisms with exponential back-off for downloading the feed.
- Archiving or deactivating products no longer present in the feed.
- Support for images and multiple variants, which are typical for an electronics retailer.
- Better error reporting (e.g., sending an email summary to the Inventory Manager if the sync fails).
- Advisory locks to strictly prevent concurrent syncs.
