-- v24 migration — remove grade 'D'. Grades are now only A, B, C
-- (customer, warehouse and admin sides). Any existing grade-'D' rows are
-- reassigned to 'C' before the CHECK constraint is tightened.

-- 1) migrate existing data off grade 'D'
UPDATE jaggery_batches  SET grade = 'C' WHERE grade = 'D';
UPDATE product_requests SET grade = 'C' WHERE grade = 'D';

-- 2) tighten the CHECK constraints back to A/B/C
ALTER TABLE jaggery_batches  DROP CONSTRAINT IF EXISTS jaggery_batches_grade_check;
ALTER TABLE jaggery_batches  ADD  CONSTRAINT jaggery_batches_grade_check  CHECK (grade IN ('A','B','C'));

ALTER TABLE product_requests DROP CONSTRAINT IF EXISTS product_requests_grade_check;
ALTER TABLE product_requests ADD  CONSTRAINT product_requests_grade_check CHECK (grade IN ('A','B','C'));
