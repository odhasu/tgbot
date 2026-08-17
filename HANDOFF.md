# ShopBot — Handoff Notes

Snapshot of everything done in this session, for starting a fresh chat with full context.

## What the bot is

Telegram marketplace bot (`aiogram 3` + `SQLAlchemy async` + `SQLite`). Layered: handlers → services → repositories → models. Admin panel for products/categories/users/orders/broadcast/stats. Customers browse categories → products → buy with internal wallet balance.

Bot: `@Vexhopbot` (id `8875874589`)
Admin Telegram ID: `6129121633`

## What changed this session

1. **Product photos** — added `photo_file_id` column to `Product` (migration `bd0fef4fd2db`).
   - Admin "Add Product" flow now asks for a photo (or Skip) as the last step.
   - Admin product detail view has a "🖼 Photo" edit button to add/replace a photo on existing products.
   - Customer-facing product view shows the photo as an image with caption if set, falls back to plain text otherwise.
   - New helper `utils/telegram.py` (`render_product_message`, `render_text_message`) handles switching a message between text and photo cleanly (Telegram can't `edit_text` a photo message, so it deletes + resends when needed).

2. **Deployment** — bot moved off local machine, now runs 24/7 in the cloud on **Render** (free tier, no card required).
   - GitHub repo: `github.com/odhasu/shopbot` (private)
   - Render service: `shopbot` → live at `https://shopbot-qijr.onrender.com`
   - Deploy is a Render **Blueprint** (`render.yaml` in repo root) — pushing to `main` on GitHub triggers redeploy.
   - Added a tiny `aiohttp` health server in `bot.py` (binds `$PORT`, returns `200 ok`) purely so Render's free web-service tier has an HTTP endpoint to consider "alive" — the actual bot still runs via long-polling, unrelated to that server.
   - Pinned Python to `3.11.15` via `PYTHON_VERSION` env var in `render.yaml` (Render defaults to 3.14, which has no prebuilt wheel for `pydantic-core` yet → build fails without the pin).
   - **UptimeRobot** free monitor pings `https://shopbot-qijr.onrender.com` every 5 min so the free Render instance never idles out (Render free tier sleeps after 15 min with no HTTP traffic, costing ~50s cold-start delay on the next message otherwise).
   - Killed the local `launchd` job (`com.oscar.shopbot.plist`, removed) that was previously running the bot on this Mac — that's no longer needed, Render is now the only running instance. Laptop can be off/closed with zero effect on the bot.

## How things are wired

- **Repo** (local + GitHub): `/Users/oscargraafmans/Documents/tg/shopbot`
- **Env vars** live in Render dashboard (Environment tab), not committed to git. Local `.env` (gitignored) has the same values for local dev/testing.
- **Database**: SQLite at `data/shopbot.db`, lives on Render's ephemeral disk. Survives sleep/wake and restarts as long as the container isn't rebuilt/redeployed. **A full redeploy wipes it** — free tier has no persistent volume. If order/user data needs to survive redeploys long-term, that's the next real gap to solve (Postgres via a free-tier provider, or upgrading Render for a persistent disk).
- **Migrations**: Alembic, in `migrations/versions/`. Render's build command runs `alembic upgrade head` automatically on every deploy.

## To manage it going forward

- **See logs / errors**: Render dashboard → shopbot service → Logs tab.
- **Redeploy after a code change**: just `git push` to `main` — Render auto-deploys. Or "Manual Deploy" button in dashboard.
- **Change env vars** (bot token, admin ids, support contact): Render dashboard → Environment tab.
- **Add another admin**: add their Telegram numeric ID to `ADMIN_IDS` env var (comma-separated), redeploy.
- **Local dev**: `cd shopbot && source .venv/bin/activate && python bot.py` — but don't run this at the same time as Render is live, Telegram only allows one poller per bot token (`TelegramConflictError` otherwise). Stop the Render service first, or just test against a second bot token.

## Session 2 (2026-07-13) — running locally, UI cleanup

1. **Bot now running locally on this Mac**, not Render. Started via:
   ```bash
   cd shopbot && source .venv/bin/activate && nohup python bot.py > logs/bot_manual.log 2>&1 &
   ```
   If Render's `shopbot` service is still live at the same time, both will poll the same bot token and one will get `TelegramConflictError`. Stop the Render service in the dashboard if you want the Mac to be the only instance, or vice versa.

2. **Section banner images** — added `utils/banners.py` (`render_banner_message`, caches Telegram `file_id` after first upload so repeat sends don't re-upload the file). Wired into:
   - `/start` and "Back to Menu" → `vex` banner
   - Shop categories screen → `shop` banner
   - Balance screen → `balance` banner
   - Profile screen → `profile` banner
   - Images live in `assets/banners/` (`vex.webp`, `shop.webp`, `balance.webp`, `topup.webp`, `profile.webp`). `topup.webp` is uploaded but unused — reserved for a real deposit-funds screen if that gets built later. These banners embed OpenAI-logo branding from wherever they were sourced — fine for a private bot, would need review before going public.

3. **Removed Vouches and Orders** from the customer-facing main menu — deleted `handlers/orders.py` and `handlers/vouches.py`, dropped their router registrations in `handlers/__init__.py` and their buttons in `keyboards/main_menu.py`. (Admin-side order management in `handlers/admin/orders.py` is untouched — that's separate.)

4. **Removed all emoji** from every bot-facing string and button label, across handlers, keyboards, and `bot.py`. Also fixed the `SUPPORT_CONTACT` placeholder → real handle `@vexaccs`, and turned Support into a real tappable link button (`https://t.me/vexaccs`) instead of plain mention text.

5. **Bug fixed**: several screens (`admin:menu` entry point, `menu:support`) used raw `message.edit_text(...)`, which throws `TelegramBadRequest: there is no text in the message to edit` when the previous message was a banner *photo* (can't `edit_text` a photo message). Fixed by routing them through the existing `utils/telegram.render_text_message` helper, which deletes+resends instead of editing when the source was a photo. **If you add new screens reachable from a banner/photo screen, use `render_text_message` or `render_banner_message`, never raw `edit_text`.**

Main menu is now: Shop, Balance, Profile, Support (+ Admin for admins).

## Known gaps / things to revisit next session

- No persistent disk — data loss risk on redeploy (see above). Still unresolved.
- Automated tests currently cover pricing and Canboso response/request parsing; handler-level tests can still be expanded.
- Photo feature only supports a single photo per product (no galleries).
- Crypto deposit addresses/QR codes exist, but transaction verification and wallet crediting are manual.
- Custom icon-image buttons (matching a reference bot's blue circle-badge icon style) were discussed and explicitly deferred — not possible via native Telegram inline buttons (text-only), would require a Telegram Mini App (WebApp) rebuild of the main menu. Decided not worth the build cost for now.

## Session 3 (2026-08-17) — FatBunny/Canboso reseller integration

- Customer catalog now comes from Canboso Telegram Buyer API v2 (the buyer key was issued through `@FatBunny_Hub_bot`). The API key is stored only in gitignored `.env`; deployment must set `CANBOSO_API_KEY` separately.
- All customer prices are computed live as wholesale price × `RETAIL_PRICE_MULTIPLIER` (currently `1.6`). Six-decimal USD wallet precision preserves the exact multiplier for sub-cent products.
- Shop UI is grouped into Accounts & Keys, Slots, and Account Upgrades, with pagination, quantity controls, stock checks, confirmation, email collection, and supported slot-duration collection.
- Purchases use the customer's local shop balance at retail. The Canboso buyer wallet pays wholesale. API idempotency prevents duplicate supplier charges, and returned credentials are delivered directly to the customer.
- Local orders now store retail revenue, supplier cost, provider order/product IDs, fulfillment status, and quantities. Admin order/stat screens show gross profit; a Supplier API screen shows upstream wallet/catalog health.
- Local product/category seeding and admin catalog routes are disabled. Legacy tables/files remain for migration compatibility.
- Crypto deposits are still manual: customers must contact support with the transaction ID for an admin balance credit.
- Current Telegram token resolves to `@Vexhopbot`; `@FatBunny_Hub_bot` is treated as the upstream supplier bot.
- At integration time the upstream API returned 56 products (49 in stock), and the upstream wallet balance was `$0.00`; it must be topped up before a real purchase can succeed.
- No local `bot.py` process was detected during this integration, and these changes were not pushed or deployed.
- The customer catalog is temporarily disabled with `CATALOG_ENABLED=false`. Set it to `true` to expose API products and allow purchases again.
