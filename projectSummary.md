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
- Which tablet/text it appears in (series, volume, fragment, line)
- How it's written in that specific occurrence
- Any determinatives or special markings
- Associated titles or epithets
- Additional notes

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
- The "query" field is automatically generated when saving
- View all instances linked to a name
- Export data

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
