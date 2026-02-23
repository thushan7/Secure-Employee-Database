from psycopg import errors
from db import get_conn

def get_employees(dept, q, order_sql):
    base_sql = f"""
    WITH dep AS (
      SELECT Essn, COUNT(*) AS dep_count FROM Dependent GROUP BY Essn
    ), w AS (
      SELECT Essn, COUNT(DISTINCT Pno) AS num_projects, COALESCE(SUM(Hours),0) AS total_hours
      FROM Works_On GROUP BY Essn
    )
    SELECT
      e.Ssn,
      (e.Fname || ' ' || e.Lname) AS full_name,
      d.Dname AS dept_name,
      COALESCE(dep.dep_count, 0)  AS num_dependents,
      COALESCE(w.num_projects, 0) AS num_projects,
      COALESCE(w.total_hours, 0)  AS total_hours
    FROM Employee e
    LEFT JOIN Department d ON d.Dnumber = e.Dno
    LEFT JOIN dep ON dep.Essn = e.Ssn
    LEFT JOIN w   ON w.Essn   = e.Ssn
    """
    where = []
    params = []

    if dept is not None:                   # only add when provided
        where.append("e.Dno = %s")
        params.append(int(dept))

    if q:                                  # only add when provided
        where.append("LOWER(e.Fname || ' ' || e.Lname) LIKE LOWER('%%' || %s || '%%')")
        params.append(q)

    if where:
        base_sql += " WHERE " + " AND ".join(where)

    base_sql += f" ORDER BY {order_sql}"

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(base_sql, params)
        return cur.fetchall()


def get_projects(order_sql):
    sql = f"""
    WITH stats AS (
      SELECT Pno,
             COUNT(DISTINCT Essn) AS headcount,
             COALESCE(SUM(Hours),0) AS total_hours
      FROM Works_On GROUP BY Pno
    )
    SELECT p.Pnumber, p.Pname,
           d.Dname AS dept_name,
           COALESCE(stats.headcount,0)   AS headcount,
           COALESCE(stats.total_hours,0) AS total_hours
    FROM Project p
    LEFT JOIN Department d ON d.Dnumber = p.Dnum
    LEFT JOIN stats ON stats.Pno = p.Pnumber
    ORDER BY {order_sql}
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, ())
        return cur.fetchall()

def get_project_assignments(pno: int):
    sql = """
    SELECT
      e.Ssn AS ssn,
      (e.Fname || ' ' || e.Lname) AS employee,
      COALESCE(w.Hours, 0) AS hours
    FROM Employee e
    LEFT JOIN Works_On w ON w.Essn = e.Ssn AND w.Pno = %s
    WHERE w.Hours IS NOT NULL
    ORDER BY employee;
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (pno,))
        return cur.fetchall()


def upsert_hours(essn:str, pno:int, hours:float):
    sql = """
    INSERT INTO Works_On (Essn, Pno, Hours)
    VALUES (%s,%s,%s)
    ON CONFLICT (Essn, Pno)
    DO UPDATE SET Hours = Works_On.Hours + EXCLUDED.Hours
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (essn, pno, hours))
        conn.commit()

def add_employee(ssn, fname, minit, lname, address, sex, salary, dno, super_ssn=None):
    """
    Insert a new employee. 'minit' must be a single char (use '-' if unknown).
    'sex' must be 'M' or 'F'.
    """
    sql = """
    INSERT INTO Employee (Ssn, Fname, Minit, Lname, Address, Sex, Salary, Dno, Super_ssn)
    VALUES (%s,  %s,    %s,    %s,    %s,     %s,  %s,     %s,  %s)
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (ssn, fname, minit, lname, address, sex, salary, dno, super_ssn))
        conn.commit()

def update_employee(ssn, address, salary, dno, super_ssn=None, sex=None, minit=None):
    """
    Update editable fields. Pass None for fields you don't want to change.
    """
    sets = ["Address=%s", "Salary=%s", "Dno=%s"]
    params = [address, salary, dno]

    if super_ssn is not None:
        sets.append("Super_ssn=%s"); params.append(super_ssn)
    if sex is not None:
        sets.append("Sex=%s"); params.append(sex)
    if minit is not None:
        sets.append("Minit=%s"); params.append(minit)

    sql = f"UPDATE Employee SET {', '.join(sets)} WHERE Ssn=%s"
    params.append(ssn)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        conn.commit()

def delete_employee(ssn):
    sql = "DELETE FROM Employee WHERE Ssn=%s"
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (ssn,))
            conn.commit()
    except errors.ForeignKeyViolation:
        raise ValueError("Cannot delete: employee is referenced by other data (projects/dependents/manager).")
    
def get_managers_summary():
    sql = """
    WITH emp_counts AS (
      SELECT Dno, COUNT(*) AS emp_count
      FROM Employee
      GROUP BY Dno
    ),
    dept_hours AS (
      SELECT e.Dno, COALESCE(SUM(w.Hours),0) AS total_hours
      FROM Employee e
      LEFT JOIN Works_On w ON w.Essn = e.Ssn
      GROUP BY e.Dno
    )
    SELECT
      (mgr.Fname || ' ' || mgr.Lname) AS manager_name,
      d.Dname AS dept_name,
      COALESCE(emp_counts.emp_count, 0) AS headcount,
      COALESCE(dept_hours.total_hours, 0) AS total_hours
    FROM Department d
    LEFT JOIN Employee mgr ON mgr.Ssn = d.Mgr_ssn
    LEFT JOIN emp_counts    ON emp_counts.Dno  = d.Dnumber
    LEFT JOIN dept_hours    ON dept_hours.Dno  = d.Dnumber
    ORDER BY d.Dname;
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()
