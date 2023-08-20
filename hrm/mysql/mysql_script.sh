#!/bin/bash

set -e
set -o pipefail

echo "Run All SQL Script"

# read -t 10 -p 'Enter Database Name : ' dbname
read  -p 'Enter Database Name : ' dbname
read  -p 'Enter User Name : ' uname
read  -s -p 'Enter Passward : ' upass
echo 

mysqladmin -u$uname -p$upass ping

# echo $?

# mysql -Bse "USE $dbname" 2> /dev/null

mysqlshow -u$uname -p$upass $dbname > /dev/null 2>&1 && echo "Database exists."
# mysqlshow -u$uname -p$upass "USE 1bd3e029a19198" 2>&1 && echo "Database exists."

if [ $? -eq 0 ]
then
    # echo $?
    # for sql_file in `ls *.sql`;

    # | sort -n # Ascending
    # | sort -nr # Descending
   
    OIFS="$IFS"
    IFS=$'\n'
    for sql_file in `find . -type f -name "*.sql" -print | sort -n`;
        do echo  "Processing $sql_file file..."
        mysql -u$uname -p$upass $dbname < "$sql_file" ;
    done
    IFS="$OIFS"
else
    # echo $?
    echo "The Database: $dbname does not exist, please specify a database that exists";
    fi