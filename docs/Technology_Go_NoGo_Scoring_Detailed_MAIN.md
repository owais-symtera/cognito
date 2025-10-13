# Technology Go/No-Go Scoring System (with Detailed Ranges & Weightages)

This documentation corresponds to the Excel file:
**Technology_Go_NoGo_Scoring_With_Groups.xlsx**

It contains all scoring parameters, organized by **Category**, with corrected non-overlapping ranges, assigned weightages, and detailed scoring ranges.

---

## 📊 Categories, Parameters & Weightages

| **Category**            | **Parameter**           | **Weightage** |
|--------------------------|-------------------------|---------------|
| Technology Go/No-Go      | Dose (mg/kg/day)        | 40%           |
| Molecular Weight         | Molecular Weight (Da)   | 30%           |
| API Characteristics      | Melting Point (°C)      | 20%           |
| Log P                    | Log P                   | 10%           |

---

## 🔎 Key Rules

1. **Next Number Rule**  
   - Each range starts from the next integer after the previous one ends.  
   - Prevents overlap between floor and ceiling values.  

2. **No Ambiguity**  
   - Every value belongs to **exactly one category**.  

3. **Exclusion Values**  
   - Any value outside the defined range is classified as **Exclusion**.  

---

## ✅ Detailed Scoring Ranges

### Technology Go/No-Go → Dose (mg/kg/day) — Weightage 40%

| Score | Transdermal | Transmucosal |
|-------|-------------|--------------|
| 9     | ≤0          | ≤0           |
| 8     | 1–2         | 1–2          |
| 7     | 3–5         | 3–5          |
| 6     | 6–8         | 6–10         |
| 5     | 9–11        | 11–15        |
| 4     | 12–15       | 16–20        |
| 3     | 16–18       | 21–30        |
| 2     | 19–22       | 31–40        |
| 1     | 23–30       | 41–50        |
| 0     | 31–50       | 51–70        |
| Excl. | >50         | >70          |

---

### Molecular Weight (Da) — Weightage 30%

| Score | Transdermal | Transmucosal |
|-------|-------------|--------------|
| 9     | ≤199        | ≤199         |
| 8     | 200–249     | 200–299      |
| 7     | 250–299     | 300–399      |
| 6     | 300–349     | 400–599      |
| 5     | 350–399     | 600–999      |
| 4     | 400–449     | 1000–1999    |
| 3     | 450–499     | 2000–2999    |
| 2     | 500–549     | 3000–3999    |
| 1     | 550–599     | 4000–4999    |
| 0     | 600–800     | 5000–10000   |
| Excl. | >800        | >10000       |

---

### API Characteristics → Melting Point (°C) — Weightage 20%

(Same for Transdermal & Transmucosal)

| Score | Range   |
|-------|---------|
| 9     | ≤49     |
| 8     | 50–89   |
| 7     | 90–129  |
| 6     | 130–169 |
| 5     | 170–209 |
| 4     | 210–249 |
| 3     | 250–279 |
| 2     | 280–309 |
| 1     | 310–339 |
| 0     | 340–380 |
| Excl. | >380    |

---

### Log P — Weightage 10%

| Score | Transdermal         | Transmucosal        |
|-------|---------------------|---------------------|
| 9     | 1–2                 | 1.6–3.2             |
| 7     | 3                   | –                   |
| 6     | –                   | 1–1.5 or 3.3–4      |
| 5     | 4–5 or 0–1          | –                   |
| 3     | 6                   | 0–0.9 or 5          |
| 0     | <0 or ≥6            | <0 or ≥6            |

---

## ⚖️ Weighted Scoring

Final weighted score is calculated as:

```
Weighted Score = (Score × Weightage)
```

Example:  
- Dose Score = 6 → Weighted = 6 × 0.40 = 2.4  
- Molecular Weight Score = 8 → Weighted = 8 × 0.30 = 2.4  
- … and so on.  

---

## 📂 File Contents

The Excel file has the following columns:  
- **Category** – Main group (Technology Go/No-Go, Molecular Weight, etc.)  
- **Parameter** – Specific property being measured  
- **Weightage** – Contribution percentage to overall score  
- **Score** – Score level (9 → 0, Exclusion)  
- **Transdermal** – Corrected scoring range for Transdermal delivery  
- **Transmucosal** – Corrected scoring range for Transmucosal delivery  

---

## 📝 Notes

This version ensures:  
- Clear structure by **Category**  
- No overlaps in ranges  
- Direct linkage to **weighted scoring**  
