## 0) Get the code
Download/unzip the submission (or open the folder you received) and `cd` into it:

```bash
cd cis3530-a4b-team

# 1) venv + deps
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


# 2) Postgres role + DB (uses your OS login name)
```bash
createuser -s "$USER" 2>/dev/null || true
createdb company 2>/dev/null || true
```


# 3) env vars (per terminal session)
```bash
export FLASK_ENV=development
export SECRET_KEY=dev
export DATABASE_URL="postgresql://$USER@localhost:5432/company"
```


# 4) load the Company schema/data (replace path to your file)
```bash
psql "$DATABASE_URL" -f /ABSOLUTE/PATH/TO/company_v3.02.sql
```


# 5) create app tables + indexes, then seed users
```bash
psql "$DATABASE_URL" -f team_setup.sql
```
# if seed_users.sql is missing, generate it:
```bash
python - <<'PY'
from werkzeug.security import generate_password_hash
open('seed_users.sql','w').write(
"INSERT INTO app_user(username,password_hash,role) VALUES "
f"('admin','{generate_password_hash('adminpass')}','admin'),"
f"('viewer','{generate_password_hash('viewerpass')}','viewer');\n")
print('Wrote seed_users.sql (admin/adminpass, viewer/viewerpass)')
PY
psql "$DATABASE_URL" -f seed_users.sql
```

# Indexes Used
## 1. idx_employee_dno (ON employee(dno))
This index speeds up queries that filter or join employees by department number. It is used in:
- The Employees page (`/`): When you filter by department, the query uses `WHERE e.Dno = ...` and joins to Department.
- The Managers page (`/managers`): When summarizing employees by department, the join and group-by use Dno.
## 2. idx_works_on_pno (ON works_on(pno))
This index speeds up queries that filter or join project assignments by project number. It is used in:
- The Projects page (`/projects`): When showing project headcount and total hours, the query groups by Pno and joins to Project.
- The Project Details page (`/projects/<pno>`): When listing all employees assigned to a project, the query joins Works_On on Pno and aggregates hours.

# 6) run
```bash
flask --app app:app run --debug
```
# visit http://127.0.0.1:5000/login


## Excel Import (Bonus +1.0)

**What it does:** Admins can upload a validated **.xlsx** file on a project’s detail page to insert/update (“upsert”) hours for that project.  
Valid rows are applied; invalid rows are skipped with a clear reason shown in a banner at the top of the page.

### Where is it?
- Navigate: **Projects → click a project name** (e.g., `/projects/30`)
- The **Choose File** and **Import Excel** controls appear **only for admin users**.

### File format (template)
- File type: **Excel .xlsx** (Numbers/Excel → *Export to Excel*).
- Sheet: first/active sheet is read.
- Expected columns (header names are case-insensitive; extra columns are ignored):
  - `SSN` – employee SSN (digits only)
  - `Hours` – positive number (e.g., `8`, `3.5`, `12.25`)
- Example:

| SSN       | Hours |
|-----------|-------|
| 200243095 | 8     |
| 359624751 | 3.5   |

> Notes  
> • Full name is **not required** and is ignored if present.  
> • Each row is applied to the **currently open project**; there is no Pno column in the file.

### Validation rules
For each row:
- **SSN** must be digits and must exist in `Employee` (otherwise the row is skipped: “No employee with SSN …”).  
- **Hours** must be a positive number (`> 0`).  
- If both are valid, the app **upserts** into `Works_On` for that `(SSN, current Pno)`.  
- A banner summarizes success (e.g., “Imported 7 row(s)”) and lists the first few problems, if any (e.g., “Row 2: Hours must be a positive number”).

### How to use / demo steps
1. Log in as admin (see *seed_users.sql* for credentials).
2. Go to **Projects → \<pick a project>**.
3. Click **Choose File**, select your `.xlsx`, then **Import Excel**.
4. You should see:
   - A success banner (and possibly a “Some rows were skipped …” message).
   - The **Hours** values in the table update immediately for the SSNs you imported.
   - The **Projects** list’s *Total Hours* reflect the change.

### Verifying with SQL (optional)
```bash
# Replace 30 with your project number
psql "$DATABASE_URL" -c "SELECT essn, hours FROM works_on WHERE pno=30 ORDER BY essn;"
