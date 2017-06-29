## Raspberry Pi Server Code for SBHS
![logo](https://community.arm.com/cfs-file/__key/communityserver-discussions-components-files/195/4064.raspberry_5F00_logo_5F00_1.png)

This repository contains the code to be used in the Raspberry Pis for the load sharing SBHS architecture.

### Setup Instructions

+ Install an operating system on the Raspberry Pi (*preferably Raspbian*). Click [here](https://www.raspberrypi.org/documentation/installation/) for further instructions on how to install *Raspbian*.
+ Install Apache
```
sudo apt-get install apache2
```
Check your installation by typing `sudo service apache2 status`

+ Install MySQL.
```
sudo apt-get install mysql-server
```
+ Download the setup script in your working directory from [here](https://gist.githubusercontent.com/coderick14/26e85f1bf2104fc461e4c60e97bff2cf/raw/977e844f4e854461c83627388000599a9b48d34b/setup_pi.sh). You can type the following command as well to download the script.
```
wget https://gist.githubusercontent.com/coderick14/26e85f1bf2104fc461e4c60e97bff2cf/raw/977e844f4e854461c83627388000599a9b48d34b/setup_pi.sh
```

+ Run the setup script. The Raspberry Pi **must be connected to the internet** for this script to execute. Make sure you have required access to this Git repository to download the source code.
```
bash setup_pi.sh
```

+ You will prompted for five fields during the execution of the script.
	+ **database host** : Enter the IP of the master server here
	+ **database user** : Enter the username who has remote access to the database. (Type *sbhs_pi* if you have followed this [README](https://github.com/coderick14/sbhs/blob/deep/README.md#instructions-for-setting-up-mysql) for the master server)
	+ **database password** : Password for the database user
	+ **database name** : The database name (Usually *sbhs*)
	+ **database port** : Type **3306** here. Unless you have explicitly specified a different port for MySQL.

##### NOTE :
Raspberry Pis **DO NOT** have an RTC (Real Time Clock). Thus, synchronizing time and date with that of the master server is an issue. Make sure that you run the script *synctime.sh* from the master server whenever a Pi reboots or a new Pi is connected. [This](https://github.com/coderick14/sbhs/blob/deep/synctime.sh) script wil sync the time of all the Raspberry Pis with that of the master server.