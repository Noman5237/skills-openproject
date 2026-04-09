# Log Time — Output Format

## Header

```
Logged N time entries (X.Xh total):
```

If there were errors:

```
Logged N time entries (X.Xh total) — M failed:
```

## Table

| Column | Format | Notes |
|--------|--------|-------|
| **WP** | `[#ID](link)` | Clickable link to the work package |
| **Subject** | Text | Work package title |
| **Project** | Text | Project name |
| **User** | Text | Who the time was logged for |
| **Hours** | `X.Xh` | Duration logged (e.g. `2h`, `4.5h`) |
| **Date** | `YYYY-MM-DD` | Date the time was spent on |
| **Comment** | Text or `—` | Description of work; `—` if not set |
| **Activity** | Text or `—` | Activity type (e.g. Development, Testing); `—` if default |

Omit the **User** column if all entries are for the authenticated user (self-logging).

## Example

Logged 2 time entries (6h total):

| WP | Subject | Project | Hours | Date | Comment | Activity |
|----|---------|---------|-------|------|---------|----------|
| [#59791](http://project.global.fintech23.xyz/work_packages/59791) | VAPT Issue Resolution - Admin App (UAT) | CityRemit CR | 4h | 2026-04-09 | Fixed XSS vulnerability | Development |
| [#57943](http://project.global.fintech23.xyz/work_packages/57943) | Market Research | Fintech- AI SDKs & PoCs | 2h | 2026-04-09 | — | — |
