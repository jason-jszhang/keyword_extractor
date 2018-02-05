#!/bin/bash

function main() 
{
    echo `date` >> /opt/company_search/program_monitor.log
    echo `ps aux |grep request_company_info |grep -v grep | awk '{print $0}'` >> /opt/company_search/program_monitor.log
    pid=`ps aux |grep request_company_info |grep -v grep | awk '{print $2}'`
    exe_time=`ps aux |grep request_company_info |grep -v grep | awk '{print $10}' |awk -F ':' '{print $1}'`
    if [ $exe_time -gt 20 ];then
    echo $pid
    echo $exe_time
    echo "kill pid: $pid" >> /opt/company_search/program_monitor.log
    `kill -9 $pid`
    fi
    echo `date`
}

echo "$0 Starting at `date +%Y%m%d-%X`" >> /opt/company_search/program_monitor.log

while (( 1 <= 5 ))  
do  
    main
    sleep 1200
done
