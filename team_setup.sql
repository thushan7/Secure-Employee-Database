CREATE TABLE IF NOT EXISTS app_user (
		id SERIAL PRIMARY KEY,
		username TEXT NOT NULL UNIQUE,
		password_hash TEXT NOT NULL,
		role TEXT NOT NULL DEFAULT 'viewer'
);


CREATE INDEX IF NOT EXISTS idx_employee_dno ON employee(dno);
CREATE INDEX IF NOT EXISTS idx_works_on_pno ON works_on(pno);

CREATE OR REPLACE VIEW employee_summary AS
WITH dep_cte AS (
	SELECT essn AS ssn, COUNT(*) AS dep_count
	FROM dependent
	GROUP BY essn
), work_cte AS (
	SELECT essn AS ssn, COUNT(DISTINCT pno) AS num_projects, COALESCE(SUM(hours),0) AS total_hours
	FROM works_on
	GROUP BY essn
)
SELECT
	e.ssn,
	(e.fname || ' ' || e.lname) AS full_name,
	d.dname AS dept_name,
	COALESCE(dep_cte.dep_count, 0) AS num_dependents,
	COALESCE(work_cte.num_projects, 0) AS num_projects,
	COALESCE(work_cte.total_hours, 0) AS total_hours
FROM employee e
LEFT JOIN department d ON d.dnumber = e.dno
LEFT JOIN dep_cte ON dep_cte.ssn = e.ssn
LEFT JOIN work_cte ON work_cte.ssn = e.ssn;

CREATE OR REPLACE VIEW project_stats AS
WITH stats AS (
	SELECT pno AS pnumber, COUNT(DISTINCT essn) AS headcount, COALESCE(SUM(hours),0) AS total_hours
	FROM works_on
	GROUP BY pno
)
SELECT
	p.pnumber,
	p.pname,
	d.dname AS dept_name,
	COALESCE(stats.headcount,0) AS headcount,
	COALESCE(stats.total_hours,0) AS total_hours
FROM project p
LEFT JOIN department d ON d.dnumber = p.dnum
LEFT JOIN stats ON stats.pnumber = p.pnumber;

INSERT INTO app_user(username,password_hash,role) VALUES
	('admin','scrypt:32768:8:1$0QjsAvkhQSb7G5j4$a92d08525748bcc0f6c023bbefc80fac44386fea25306a506c1bedf3789106d49bb18317b42e3a2e27d8a50fdcfeec5a9de907b8894618f15c93e00dafe1616a','admin'),
	('viewer','scrypt:32768:8:1$s87xftoGqylNhlDC$03e253c987e69294223a5744a22d4b42623de003e692ee46220d254a9816ce671c01fb6f77cb902654b71434ba4b67d3705dec60852911dd404872d91ea3f984','viewer')
ON CONFLICT (username) DO NOTHING;