DELIMITER //


DROP VIEW  IF EXISTS `Insurance_View`//

CREATE 
    ALGORITHM = UNDEFINED 
    DEFINER = `avuadmin`@`%` 
    SQL SECURITY DEFINER
VIEW `Insurance_View` AS
    SELECT 
        `ID`.`employee` AS `employee`,
        `I`.`insurance_end_date` AS `insurance_end_date`,
        `I`.`insurance_start_date` AS `insurance_start_date`,
        `ID`.`parent` AS `parent`,
        CASE
            WHEN `ID`.`inactive` = 0 THEN `I`.`inactive`
            ELSE `ID`.`inactive`
        END AS `Istatus`
    FROM
        (`tabInsurance` `I`
        LEFT JOIN `tabInsurance Details` `ID` ON (`ID`.`parent` = `I`.`name`))

   //


DELIMITER ;
