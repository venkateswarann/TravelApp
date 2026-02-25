# 🌍 Travel Planner App

A beautiful, mobile-first web app to plan and track your Europe trip (UK → Switzerland → Paris → UK).

## Features

### 📅 Itinerary Planner
- Add daily travel plans with from/to locations
- Select transport mode (train, flight, bus, car, ferry)
- Auto-estimate travel times
- Store departure times and notes

### 🏨 Hotel Management
- Add hotel booking URLs
- Auto-scrape hotel info (address, name)
- Track check-in/check-out dates
- Store location notes

### ✈️ Travel Documents
- Store flight/train/bus details
- Upload PDF boarding passes/tickets
- Track booking references and seat numbers
- View documents instantly during travel

### 💰 Expense Tracking
- Add expenses with categories
- Multi-currency support (EUR, CHF, GBP)
- Split bills between you and friends
- Real-time balance calculation

### 📱 Mobile-First Design
- Responsive layout for phones/tablets
- Fast loading with offline capability
- Touch-friendly interface
- Tailscale MagicDNS access from anywhere

## Quick Start

### 1. Launch the App

```bash
cd ~/travel-app
./run.sh
```

The script will:
- Create Python virtual environment
- Install dependencies
- Initialize database
- Start the Flask server

### 2. Access the App

**Via Tailscale (recommended):**
- From your Jetson: http://localhost:5000
- From any device on Tailnet: http://jetsonvivek:5000 or http://jetsonvivek.tailnetname.ts.net:5000

**Without Tailscale:**
- Only from Jetson: http://localhost:5000

### 3. Start Using

1. Open the app URL in your browser
2. The "Europe Adventure 2024" trip is pre-loaded
3. Navigate tabs to add your plans

## Adding Your Trip Details

### 📝 Itinerary
- Go to "Itinerary" tab
- Fill from/to locations, dates, transport
- Add rough daily plans in notes
- View timeline by date

### 🏨 Hotels
- Paste booking URL from Booking.com, Airbnb, etc.
- App auto-extracts hotel name and address
- Add check-in/out dates
- View all hotels in cards

### ✈️ Travel Info
- Add flight/train/bus numbers
- Upload PDF tickets
- Track departure/arrival times
- Download/view PDFs on mobile during travel

### 💰 Expenses
- Add expense description & amount
- Select currency and category
- Choose who paid
- See automatic balance/split calculation
- View who owes who what

## File Structure

```
travel-app/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── run.sh                      # Launcher script
├── travel.db                   # SQLite database (created automatically)
├── uploads/                    # PDF storage directory
├── templates/
│   ├── base.html              # Base layout
│   ├── index.html              # Trip list
│   └── trip_detail.html        # Trip management
└── static/
    ├── css/style.css           # Beautiful mobile-first CSS
    └── js/app.js               # Interactive features
```

## Technologies

- **Backend:** Flask, SQLite, SQLAlchemy
- **Frontend:** HTML5, CSS3, Vanilla JS
- **Design:** Mobile-first, responsive, modern gradients
- **Libraries:** Font Awesome, HTMX, QRCode.js
- **Access:** Tailscale MagicDNS

## Mobile Access via Tailscale

Since you'll access this during travel:

1. Ensure Tailscale is running on Jetson:
   ```bash
   sudo systemctl start tailscaled
   ```

2. Use MagicDNS names:
   - Short: http://jetsonvivek:5000
   - Full: http://jetsonvivek.your-tailnet.ts.net:5000

3. Save to phone home screen (add to homescreen)
4. Access PDFs and info offline during travel

## Tips

### During Travel
- Bookmark the URL on your phone
- Add to home screen for app-like experience
- Download PDFs before travel for offline access
- Use expense tracking to split costs fairly

### Adding Friends to Expenses
- In "Paid By" field, add your name (e.g., "Vivek") and friend's name (e.g., "John")
- App automatically calculates who owes who
- Balance shows at top of expenses tab

### Transport Time Estimation
- App auto-suggests travel times for common routes
- Works for London → Paris, Paris → Zurich, etc.
- Adjust manually if needed

### Hotel Info Scraping
- Works with Booking.com, Airbnb, Hotels.com
- Extracts hotel name, address, coordinates
- May need manual correction for some sites

## Backup Your Data

The database is stored locally. To back up:

```bash
cp ~/travel-app/travel.db ~/backups/travel-backup-$(date +%Y%m%d).db
```

All PDFs are in `~/travel-app/uploads/`

## Troubleshooting

**"Database locked" error:**
- Another instance is running. Kill it:
  ```bash
  pkill -f app.py
  ```

**Can't access Tailscale:**
- Check Tailscale status: `tailscale status`
- Restart Tailscale: `sudo systemctl restart tailscaled`
- Get new IP: `tailscale ip`

**PDF upload errors:**
- Max size: 50MB
- Allowed formats: PDF, JPG, PNG
- Check disk space: `df -h`

**Dependencies not installing:**
- Update pip: `pip install --upgrade pip`
- Install manually: `pip install -r requirements.txt`

## Customization

### Change Trip Name
Edit `app.py` around line 110:
```python
name='Europe Adventure 2024'
```

### Change Default Currency
Edit `models.py` Expense class:
```python
currency = db.Column(db.String(3), default='EUR')
```

### Add Categories
Edit templates, look for `<select name="category">`

## Security Notes

- App runs on local network only (0.0.0.0)
- Tailscale provides encrypted VPN access
- Use strong Tailnet password
- PDFs stored locally, not cloud
- Database not encrypted (consider for sensitive trips)

## Future Enhancements

- Offline PWA support
- Map integration with hotel locations
- Weather forecast for travel dates
- Packing list generator
- Photo gallery for trip memories
- Multi-trip dashboard
- CSV/PDF export

---

**Enjoy your Europe trip!** 🇬🇧 → 🇨🇭 → 🇫🇷 🇬🇧

*Built with 💙 by OpenClaw Assistant*
