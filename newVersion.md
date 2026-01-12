# LAMAN - Hittite Name Finder

## What Is This App?

LAMAN is a searchable database of ancient Hittite names. The Hittites were an ancient Anatolian civilization (modern-day Turkey), and their names appear in cuneiform clay tablets. This tool helps researchers find and study these names.

---

## What Can Users Do?

### 1. Search for Names
Users can type a name (or part of a name) in the search box to find matching Hittite names. The search is **smart** - it doesn't care about:
- Accents or special characters (searching "kataha" finds "Kattaḫḫa")
- Double letters (searching "kata" finds "Kattaḫḫa")  
- Similar sounds like g/k, b/p, d/t (searching "gadaha" finds "Kattaḫḫa")

Users can also use **regex patterns** for advanced searches (e.g., searching `^A.*li$` finds all names starting with A and ending with "li").

### 2. Filter Names by Category
Users can narrow down results using three filters:

**Type of Name:**
- Divine Names (gods/deities) - shown in purple
- Personal Names (people) - shown in blue  
- Geographical Names (places) - shown in green

**How It's Written:**
- Phonetic (spelled out syllable by syllable)
- Logographic (using word-signs/Sumerograms)
- Akkadographic (using Akkadian writing conventions)

**Completeness:**
- Complete names
- Incomplete (partially damaged/missing)
- Acephalous (missing the beginning)

### 3. View Name Details
Clicking on any name opens a popup showing:
- The name with its determinative (classifier symbol)
- The name in cuneiform script (when available)
- **Variant forms** - different spellings of the same name
- **Correspondences** - names that were equated with each other (e.g., a Hittite god identified with a Sumerian god)
- **Attestations** - list of tablets where this name appears, with links to the HPM database (Hethitologie Portal Mainz)
- **Literature** - scholarly references about this name

### 4. Export Search Results (CSV)
Users can export their current search results to CSV:
- Click the "Export CSV" button after performing a search
- Downloads a CSV file with all matching names and their details
- Includes: name, type, spelling, completeness, variant forms, correspondences
- Useful for researchers who want to analyze data in Excel or other tools

---

## What Data Is Stored?

### Names
Each name entry contains:
- The clean/normalized name for display
- What type it is (deity, person, or place)
- How it's written (phonetic, logographic, akkadographic)
- Whether it's complete or fragmentary
- Related names and variant spellings
- Bibliography and scholarly notes
- A special "query" field that stores a simplified version for searching

### Instances (Attestations)
Each occurrence of a name in a text is recorded with:
- Which tablet/text it appears in (linked to proper tables - see below)
- How it's written in that specific occurrence
- Any determinatives or special markings
- Associated titles or epithets
- Additional notes

### NEW: Publication Structure (Normalized Tables)

In the old version, tablet references were stored as plain text (e.g., "KBo 40 123 iv 5"). In the new version, this is properly structured:

**Series Table**
- `id` - Primary key
- `abbreviation` - e.g., "KBo", "KUB", "CTH", "VBoT"

**Volume Table**
- `id` - Primary key
- `series_id` → Foreign key to Series
- `number` - Volume number (e.g., 40)


**Fragment Table**
- `id` - Primary key
- `volume_id` → Foreign key to Volume
- `number` - Fragment number (e.g., 123)


**Instance Table (Updated)**
- `id` - Primary key
- `name_id` → Foreign key to Name
- `fragment_id` → Foreign key to Fragment
- `line` - Line reference (e.g., "iv 5", "obv. 12")
- `writing` - How the name is written here
- `determinative` - Determinative used
- `notes` - Additional notes
- ... (other existing fields)

**Relationship Diagram:**
```
Series (KBo, KUB, etc.)
  └── Volume (KBo 40, KBo 41, etc.)
        └── Fragment (KBo 40.123, KBo 40.124, etc.)
              └── Instance (Name X at KBo 40.123 line iv 5)
                    └── Name (the actual name entry)
```

### NEW: Search by Publication

Users can now:
1. **Browse by Series** - See all names attested in KBo, KUB, etc.
2. **Browse by Volume** - See all names in KBo 40
3. **Browse by Fragment** - See all names on a specific tablet
4. **Search tablets** - Type "KBo 40" to find all fragments in that volume
5. **Reverse lookup** - Click a series/volume to see which names appear there

---

## How Does the Search Work?

When a name is added to the database, the system creates a "query" version by:
1. Making it lowercase
2. Removing accents (ḫ becomes h, š becomes s, etc.)
3. Treating similar sounds the same (g=k, b=p, d=t)
4. Removing punctuation and special characters
5. Collapsing repeated letters

This means "Kattaḫḫa" becomes "kataha" internally, so users can find it no matter how they type it.

The search also looks at variant forms and correspondences, so searching for one variant finds the main entry.

---

## Admin Features

Administrators can:
- Add, edit, and delete names
- Add attestations (instances) linked to names
- Add/manage Series, Volumes, and Fragments
- The "query" field is automatically generated when saving
- View all instances linked to a name

### CSV Export (Admin)
Admins have full database export capabilities:
- **Export All Names** - Complete dump of all names with all fields
- **Export All Instances** - All attestations with publication references
- **Export All Fragments** - List of all tablets in the database
- **Export by Table** - Choose which table to export (Names, Instances, Series, Volumes, Fragments)
- Exports include related data (e.g., Instance export includes Series/Volume/Fragment info)
- Available directly from Django Admin interface via "Export" action

---

## Who Made This?

- **M. Ali Akman** (Bilkent University) - Developer
- **Michele Cammarosano** (University of Naples 'L'Orientale') - Content/Research

Part of the LAMAN project, building on earlier work by Eileen Xing and Hartmut Oertel from a DFG-funded project on Hittite cult inventories.

---

## Frontend Details

### Page Layout
The main page has:
- **Header**: LAMAN logo + university logos (Bilkent, Naples)
- **Search mode toggle**: "Names" button (active) and "Tablets" button (for future tablet search)
- **Search method toggle**: "Regex" (default, enabled) or "Normal" (substring search)
- **Search bar**: Text input that searches as you type
- **Filter panels**: Three collapsible sections for Type, Spelling, and Completeness
- **Results grid**: Colored buttons for each matching name
- **Footer**: Project credits and license info (fixed at bottom)

### How the Search Works (Frontend Side)
1. User types in the search box
2. On every keystroke, the `searchTags()` function runs
3. The input is **normalized** (same logic as backend - lowercase, remove accents, collapse duplicates)
4. A POST request is sent to `/api/search/` with:
   - The normalized query
   - Whether regex mode is on
   - Current filter selections (type, spelling, completeness)
5. The server returns matching names
6. The `createTags()` function clears the results area and creates a colored button for each name

### Color Coding
Names are displayed as buttons with colors based on type:
- **Purple** - Divine names (deities/gods)
- **Blue** - Personal names (people)
- **Green** - Geographical names (places)

### Detail Modal
When a user clicks a name button:
1. The `detail()` function fetches full data from `/api/detail/{id}/`
2. The `detailMaker()` function builds the modal content:
   - Name with determinative as superscript
   - Cuneiform rendering (if possible)
   - Correspondences section
   - Variant forms section
   - Literature/notes section
   - Attestations list with clickable links to HPM database
3. The Materialize modal opens with this content

### Cuneiform Display
The app can show names in actual cuneiform script:
1. `converter.js` takes a romanized name
2. `shaper()` breaks it into syllables (CV, CVC, VC, V patterns)
3. Each syllable is looked up in `unicodedata.js` (3000+ cuneiform sign mappings)
4. The matching Unicode cuneiform characters are displayed
5. Uses "UllikummiA" font for proper cuneiform rendering

### Filter Buttons
Each filter group works the same way:
1. Clicking a filter button marks it as "disabled" (selected) and un-disables others
2. Updates the `filterArray` with current selections
3. Triggers a new search with the updated filters
4. Server filters results and returns only matching names

### Static Files Summary
| File | Purpose |
|------|---------|
| `script.js` | Main app logic - search, filters, modal, API calls |
| `converter.js` | Converts romanized text to cuneiform Unicode |
| `unicodedata.js` | Lookup table of 3000+ cuneiform signs with Unicode values |
| `style.css` | Custom styling (colors, layout, footer) |
| `unicode.css` | Loads cuneiform font (UllikummiA.ttf) |
| `UllikummiA.ttf` | Cuneiform font file |
| `laman.png` | Project logo |
| `logo Napoli.png` | Naples university logo |
| `ex1-8.png, regex.png` | Screenshots for help page |

### External Libraries (loaded from CDN)
- **Materialize CSS 1.0.0** - UI components (buttons, modals, collapsibles, grid)
- **Axios** - HTTP requests to the API
- **Google Fonts (Raleway)** - Body text font
- **Material Icons** - Icons for UI elements

---


# Suggested Simplified Stack for Rebuild

```
Backend:
├── Python 3.11+
├── Django 5.x (latest LTS)
├── Django REST Framework
├── SQLite database
└── Gunicorn (production server)

Frontend:
├── Vanilla HTML/CSS/JS (no build step)
├── Tailwind CSS (via CDN or build)
├── Alpine.js (for interactivity) OR vanilla JS
├── Native fetch() instead of Axios
└── Keep the cuneiform converter as-is

Deployment:
├── Single VPS or shared hosting
├── Nginx as reverse proxy (optional)
└── No Docker needed for this scale
```

---

### What to Keep vs Change

**Keep (works well):**
- Django backend architecture
- REST API design (`/api/search/`, `/api/detail/`)
- Normalization algorithm (both frontend and backend)
- Cuneiform converter logic
- Color-coded type display

**Must Change (new requirements):**
- Data model: Split Instance into Series → Volume → Fragment → Instance hierarchy
- Add new API endpoints for browsing by publication
- Add frontend UI for tablet/volume browsing
- Migration script to parse old text-based references into new structure

**Consider Changing:**
- Materialize CSS → Tailwind (or keep if time-limited)
- Axios → native fetch()
- MySQL → SQLite
- jQuery dependency → remove (Materialize brings it)

**Optional Improvements:**
- Add debouncing to search (wait 300ms after typing stops)
- Cache initial data load in localStorage
- Add loading spinner during searches
- Lazy-load the unicodedata.js (it's large)

---

### Minimal Viable Rebuild

If starting fresh with minimal effort:

1. **Create new Django project** with SQLite
2. **Create new models.py** with normalized structure:
   - `Name` (keep as-is, change `managed = True`)
   - `Series` (new)
   - `Volume` (new, FK to Series)
   - `Fragment` (new, FK to Volume)
   - `Instance` (updated, FK to Fragment instead of text fields)
3. **Write migration script** to parse old "KBo 40 123" text into proper tables
4. **Copy admin.py** - add admin for Series/Volume/Fragment
5. **Update serializers.py** - nested serializers for publication hierarchy
6. **Update views.py** - add endpoints for browsing by publication
7. **Update frontend** - add tablet/volume browse UI

Estimated time: 6-10 hours for a working version (more complex than before due to new data model).

---

### New API Endpoints Needed

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/series/` | GET | List all series (KBo, KUB, etc.) |
| `/api/series/<id>/volumes/` | GET | List volumes in a series |
| `/api/volumes/<id>/fragments/` | GET | List fragments in a volume |
| `/api/fragments/<id>/` | GET | Get fragment details with all names |
| `/api/search/tablets/` | POST | Search tablets by publication ref |
| `/api/export/csv/` | POST | **User CSV export** - export current search results |

### CSV Export Implementation

**User Export (`/api/export/csv/`):**
- Accepts same parameters as `/api/search/` (query, filters)
- Returns CSV file download instead of JSON
- Columns: Name, Type, Spelling, Completeness, Variants, Correspondences, Literature
- Optional: Include attestations (expandable rows)

**Admin Export (Django Admin):**
- Add `ExportMixin` to all ModelAdmin classes
- Use `django-import-export` library OR custom admin action
- Export actions: "Export selected as CSV", "Export all as CSV"
- Related data automatically joined (Instance export includes Series/Volume/Fragment names)

---

### Data Migration Strategy

Your old Instance records have text like "KBo 40 123 iv 5". To migrate:

```python
# Pseudo-code for migration
for instance in old_instances:
    # Parse "KBo 40 123" from occurrence field
    parts = instance.occurrence.split()
    series_abbr = parts[0]  # "KBo"
    vol_num = parts[1]      # "40"
    frag_num = parts[2]     # "123"
    line = " ".join(parts[3:])  # "iv 5"
    
    # Get or create Series
    series, _ = Series.objects.get_or_create(abbreviation=series_abbr)
    
    # Get or create Volume
    volume, _ = Volume.objects.get_or_create(series=series, number=vol_num)
    
    # Get or create Fragment
    fragment, _ = Fragment.objects.get_or_create(volume=volume, number=frag_num)
    
    # Update Instance
    instance.fragment = fragment
    instance.line = line
    instance.save()
```

---

## Technical Notes for Rebuilding

**Stack:** Django (Python) backend with REST API, Materialize CSS frontend

**Key Files:**
- `namefinder/models.py` - Database structure (Name and Instance tables)
- `namefinder/views.py` - API endpoints for search and detail retrieval
- `namefinder/admin.py` - Admin interface with auto-normalization
- `namefinder/static/script.js` - Frontend search and display logic
- `namefinder/static/converter.js` - Cuneiform conversion
- `namefinder/static/unicodedata.js` - Cuneiform sign database
- `namefinder/templates/namefinder/index.html` - Main search page
- `namefinder/templates/namefinder/help.html` - User guide with screenshots
