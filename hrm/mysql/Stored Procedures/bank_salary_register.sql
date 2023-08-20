DELIMITER //

DROP PROCEDURE IF EXISTS `BankSalaryRegister`//
CREATE DEFINER=`avuadmin`@`%` PROCEDURE `BankSalaryRegister`(p_company VARCHAR(255),
p_employee VARCHAR(255),
p_docstatus VARCHAR(25),
p_startdate VARCHAR(25),
p_enddate VARCHAR(25))
begin
select 
-- `tabSalary Slip`.name '01# رقم الهوية:Link/Salary Slip:200',
tabEmployee.id_number '10# رقم الهوية :Data:200',
`tabSalary Slip`.total_deduction + `tabSalary Slip`.total_loan_repayment '09# المستقطع:Float:200',
osc.amount '08# البدلات الاخرى :Float:200',
sc.amount '07# بدل السكن:Float:200',
bsc.amount '06# الراتب الاساسي :Float:200',
'راتب' as '05#  تفاصيل التحويل :Data:200',
tabEmployee.bank_name  '04#  بنك المستفيد :Data:200',
tabEmployee.full_name_in_arabic  '03# اسم المستفيد :Data:200',
tabEmployee.bank_ac_no  '02# رقم الايبان :Data:200',
`tabSalary Slip`.net_pay  '01# المبلغ الاجمالي :Float:200'
from `tabSalary Slip` 
inner join tabEmployee on `tabSalary Slip`.employee = tabEmployee.name
left outer join 
(select `tabSalary Slip`.name ,sum(`tabSalary Detail`.amount) as 'amount' from
`tabSalary Slip` inner join `tabSalary Detail` on `tabSalary Detail`.parent= `tabSalary Slip`.name 
inner join `tabSalary Component` on `tabSalary Detail`.salary_component = `tabSalary Component`.name and `tabSalary Component`.type='Earning' 
and `tabSalary Component`.salary_component_abbr in ('H','HA') where  `tabSalary Slip`.docstatus=p_docstatus and `tabSalary Slip`.start_date>=p_startdate and `tabSalary Slip`.end_date<=p_enddate
group by `tabSalary Slip`.name ) 
as sc on  sc.name=`tabSalary Slip`.name 
left outer join
(select `tabSalary Slip`.name,sum(`tabSalary Detail`.amount) as 'amount' from 
`tabSalary Slip` inner join `tabSalary Detail` on `tabSalary Detail`.parent= `tabSalary Slip`.name 
inner join `tabSalary Component` on `tabSalary Detail`.salary_component = `tabSalary Component`.name and `tabSalary Component`.type='Earning' 
and `tabSalary Component`.salary_component_abbr in ('BC','B') where  `tabSalary Slip`.docstatus=p_docstatus 
and `tabSalary Slip`.start_date>=p_startdate and `tabSalary Slip`.end_date<=p_enddate
group by `tabSalary Slip`.name) as bsc on bsc.name=`tabSalary Slip`.name 
left outer join
(select `tabSalary Slip`.name,sum(`tabSalary Detail`.amount) as 'amount' from `tabSalary Slip` inner join `tabSalary Detail` on `tabSalary Detail`.parent= `tabSalary Slip`.name 
inner join `tabSalary Component` on `tabSalary Detail`.salary_component = `tabSalary Component`.name and `tabSalary Component`.type='Earning' 
and `tabSalary Component`.salary_component_abbr not in ('H','HA','BC','B') where  `tabSalary Slip`.docstatus=p_docstatus 
and `tabSalary Slip`.start_date>=p_startdate and `tabSalary Slip`.end_date<=p_enddate
group by `tabSalary Slip`.name) as osc on osc.name=`tabSalary Slip`.name 
where `tabSalary Slip`.docstatus=p_docstatus and `tabSalary Slip`.company=p_company and `tabSalary Slip`.employee=ifnull(p_employee,`tabSalary Slip`.employee)
and `tabSalary Slip`.start_date>=p_startdate and `tabSalary Slip`.end_date<=p_enddate
group by `tabSalary Slip`.name; 
end//

DELIMITER ;