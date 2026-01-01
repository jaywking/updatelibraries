@echo off
setlocal EnableDelayedExpansion

echo ==================================================
echo  Removing Azure Python SDK + CLI Libraries
echo  Safe Mode - Core libs preserved
echo ==================================================
echo.

REM --- Timestamp for files ---
set TS=%DATE:~-4%-%DATE:~4,2%-%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%
set TS=%TS: =0%

REM --- Backup file ---
set BACKUP=PRE_AZURE_REMOVAL_BACKUP_%TS%.txt
echo Creating full package backup: %BACKUP%
pip freeze > %BACKUP%

REM --- Log file ---
set LOGFILE=azure_uninstall_%TS%.log
echo Logging to %LOGFILE%
echo Start: %DATE% %TIME% > %LOGFILE%
echo Backup: %BACKUP% >> %LOGFILE%

REM --- Azure CLI ---
pip uninstall -y azure-cli >> %LOGFILE%
pip uninstall -y azure-cli-core >> %LOGFILE%
pip uninstall -y azure-cli-telemetry >> %LOGFILE%

REM --- Base legacy Azure ---
pip uninstall -y adal >> %LOGFILE%
pip uninstall -y azure-common >> %LOGFILE%
pip uninstall -y msrest >> %LOGFILE%
pip uninstall -y msrestazure >> %LOGFILE%

REM --- Azure Core SDK (kept minimum auth only)
pip uninstall -y azure-appconfiguration >> %LOGFILE%
pip uninstall -y azure-batch >> %LOGFILE%
pip uninstall -y azure-cosmos >> %LOGFILE%
pip uninstall -y azure-data-tables >> %LOGFILE%
pip uninstall -y azure-datalake-store >> %LOGFILE%
pip uninstall -y azure-functions >> %LOGFILE%
pip uninstall -y azure-monitor-query >> %LOGFILE%
pip uninstall -y azure-multiapi-storage >> %LOGFILE%
pip uninstall -y azure-storage-blob >> %LOGFILE%
pip uninstall -y azure-storage-common >> %LOGFILE%

REM --- Key Vault ---
pip uninstall -y azure-keyvault-administration >> %LOGFILE%
pip uninstall -y azure-keyvault-certificates >> %LOGFILE%
pip uninstall -y azure-keyvault-keys >> %LOGFILE%
pip uninstall -y azure-keyvault-secrets >> %LOGFILE%
pip uninstall -y azure-keyvault-securitydomain >> %LOGFILE%

REM --- Synapse ---
pip uninstall -y azure-synapse-accesscontrol >> %LOGFILE%
pip uninstall -y azure-synapse-artifacts >> %LOGFILE%
pip uninstall -y azure-synapse-managedprivateendpoints >> %LOGFILE%
pip uninstall -y azure-synapse-spark >> %LOGFILE%

REM --- AI / Agent SDK ---
pip uninstall -y azure-ai-agents >> %LOGFILE%
pip uninstall -y azure-ai-projects >> %LOGFILE%

REM --- ALL Management SDKs ---
for %%A in (
azure-mgmt-advisor
azure-mgmt-apimanagement
azure-mgmt-appconfiguration
azure-mgmt-appcontainers
azure-mgmt-applicationinsights
azure-mgmt-authorization
azure-mgmt-batch
azure-mgmt-batchai
azure-mgmt-billing
azure-mgmt-botservice
azure-mgmt-cdn
azure-mgmt-cognitiveservices
azure-mgmt-compute
azure-mgmt-containerinstance
azure-mgmt-containerregistry
azure-mgmt-containerservice
azure-mgmt-cosmosdb
azure-mgmt-databoxedge
azure-mgmt-datamigration
azure-mgmt-devtestlabs
azure-mgmt-dns
azure-mgmt-eventgrid
azure-mgmt-eventhub
azure-mgmt-extendedlocation
azure-mgmt-hdinsight
azure-mgmt-imagebuilder
azure-mgmt-iotcentral
azure-mgmt-iothub
azure-mgmt-iothubprovisioningservices
azure-mgmt-keyvault
azure-mgmt-loganalytics
azure-mgmt-managementgroups
azure-mgmt-maps
azure-mgmt-marketplaceordering
azure-mgmt-media
azure-mgmt-monitor
azure-mgmt-msi
azure-mgmt-mysqlflexibleservers
azure-mgmt-netapp
azure-mgmt-policyinsights
azure-mgmt-postgresqlflexibleservers
azure-mgmt-privatedns
azure-mgmt-rdbms
azure-mgmt-recoveryservices
azure-mgmt-recoveryservicesbackup
azure-mgmt-redhatopenshift
azure-mgmt-redis
azure-mgmt-resource
azure-mgmt-resource-deployments
azure-mgmt-resource-deploymentscripts
azure-mgmt-resource-deploymentstacks
azure-mgmt-resource-templatespecs
azure-mgmt-search
azure-mgmt-security
azure-mgmt-servicebus
azure-mgmt-servicefabric
azure-mgmt-servicefabricmanagedclusters
azure-mgmt-servicelinker
azure-mgmt-signalr
azure-mgmt-sql
azure-mgmt-sqlvirtualmachine
azure-mgmt-storage
azure-mgmt-synapse
azure-mgmt-trafficmanager
azure-mgmt-web
) do (
    pip uninstall -y %%A >> %LOGFILE%
)

echo.
echo ==================================================
echo  Azure SDK removal completed.
echo  Backup: %BACKUP%
echo  Log saved to: %LOGFILE%
echo ==================================================
pause
