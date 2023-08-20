DELIMITER $$


DROP PROCEDURE IF EXISTS `salary_structure`;
CREATE PROCEDURE `salary_structure`(p_company VARCHAR(255), p_employee VARCHAR(255), p_from_date DATE, p_nationality VARCHAR(255))
BEGIN
	SET @row_number = 6;

	SET @sql_dynamic = (
	SELECT
		GROUP_CONCAT(DISTINCT
			CONCAT('GROUP_CONCAT(DISTINCT(
				IF(`SD`.`salary_component` = "',SD.salary_component,'",
					IF(`SD`.`amount_based_on_formula` = 1,
						IF(`SD`.`parentfield` = "deductions",
							IF(CHAR_LENGTH(TRIM(`SD`.`formula`)) > 0,CONCAT("-1 * (",`SD`.`formula`,")"),0)
						,IF(CHAR_LENGTH(TRIM(`SD`.`formula`)) > 0,`SD`.`formula`,0)),
					IF(`SD`.`parentfield` = "deductions",-1 * `SD`.`amount`,`SD`.`amount`)),
				null)
				))AS "',LPAD(SD.idx,2,0),'#',SD.salary_component,':Float:100",
				GROUP_CONCAT(DISTINCT(
					IF(`SD`.`salary_component` = "',SD.salary_component,'",
						IF(`SD`.`amount_based_on_formula` = 1,
							IF(`SD`.`parentfield` = "deductions",
								IF(CHAR_LENGTH(TRIM(`SD`.`formula`)) > 0,CONCAT("-1 * (",`SD`.`formula`,")"),0)
							,IF(CHAR_LENGTH(TRIM(`SD`.`formula`)) > 0,`SD`.`formula`,0)),
						IF(`SD`.`parentfield` = "deductions",-1 * `SD`.`amount`,`SD`.`amount`)),
					null)
				))AS `',SD.abbr,'`'
			)
		)
	FROM (SELECT (@row_number := @row_number + 1) AS idx,SD.*
		FROM(SELECT DISTINCT `SC`.`name` AS `salary_component`,`SC`.`salary_component_abbr` AS `abbr`,`SD`.`parentfield`
			FROM `tabSalary Detail` AS `SD`
			INNER JOIN `tabSalary Component` AS `SC`
				ON `SC`.`name` = `SD`.`salary_component`
			WHERE `SD`.`docstatus` = 1
			AND `SD`.`parenttype` = 'Salary Structure'
			GROUP BY `SD`.`salary_component`, `SD`.`parentfield`
			ORDER BY `SD`.`parentfield` DESC,`SC`.`name`) AS SD)SD
	);
	
	SET @column = IF(@sql_dynamic IS NOT NULL,concat(",",@sql_dynamic),'');

	SET @p_employee =  IF(p_employee IS NOT NULL,concat('"',p_employee,'"'),"`E`.`name`");
	SET @nationality = IF(p_nationality IS NOT NULL,concat('"',p_nationality,'"'),"`E`.`saudi_or_nonsaudi`");

	SET @sql = CONCAT('SELECT `SSA`.`employee` AS "01#Employee:Link/Employee:100" ,`SSA`.`employee_name` AS "02#Employee Name:Data:150",`SS`.`name` AS "03#Salary Structure:Link/Salary Structure:100",`SSA`.`from_date` AS `04#From Date:Date:100`, `SSA`.`base` AS "06#Base:Currency:100", `SSA`.`base`, 30 AS payment_days, 30 AS total_working_days, 0 AS leave_without_pay, 0 AS absent_days',
		@column,
		'FROM `tabSalary Structure Assignment` AS `SSA`
		LEFT JOIN `tabSalary Structure` AS `SS`
			ON `SSA`.`salary_structure` = `SS`.`name`
		LEFT JOIN `tabSalary Detail` AS `SD`
			ON `SS`.`name` = `SD`.`parent`
		LEFT JOIN `tabEmployee` AS `E`
			ON `SSA`.`employee` = `E`.`name`
		WHERE `SS`.`docstatus` = 1
		AND `SS`.`is_active` = "YES"
		AND `SS`.`company` = "',p_company,'"
		AND `E`.`name` = ',@p_employee,'
		AND `E`.`saudi_or_nonsaudi` = ',@nationality,'
		AND `SSA`.`from_date` >= "',p_from_date,'"
		GROUP BY `SSA`.`employee`, `SSA`.`salary_structure`');

	PREPARE stmt FROM @sql;
	EXECUTE stmt;
	DEALLOCATE PREPARE stmt;
END;  $$


DELIMITER ;
