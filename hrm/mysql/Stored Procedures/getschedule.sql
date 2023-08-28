DELIMITER //

DROP PROCEDURE IF EXISTS `getschedule`//
CREATE DEFINER=`root`@`localhost` PROCEDURE `getschedule`(p_Fromdate DATETIME, p_Todate DATETIME, p_Startdate DATETIME)
BEGIN
	DECLARE _dayDiff INT DEFAULT 0;
	SET _dayDiff = DATEDIFF(p_Startdate, p_Fromdate);

	SELECT employee_name, DATE_FORMAT(DATE_ADD(attendance_date, INTERVAL _dayDiff DAY),'%Y-%m%-%d') AS attendance_date, store, shift_time
	FROM `tabShift Schedule`
	WHERE attendance_date BETWEEN p_Fromdate AND p_Todate;
END//

DELIMITER ;