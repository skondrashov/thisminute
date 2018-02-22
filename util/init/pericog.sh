cd;
sudo chmod 777 /srv;
wget http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/cuda-repo-ubuntu1604_9.0.176-1_amd64.deb;
sudo dpkg -i cuda-repo-ubuntu1604_9.0.176-1_amd64.deb;
rm cuda-repo-ubuntu1604_9.0.176-1_amd64.deb;
sudo apt-key adv --fetch-keys http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/7fa2af80.pub;
sudo apt-get update;
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password password $PERICOG_SQL_ROOT_PASSWORD';
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password $PERICOG_SQL_ROOT_PASSWORD';
sudo apt-get -y install mysql-server cuda;
pip install --upgrade pip;
sudo pip install postgresql numpy scipy unidecode;
sudo pip install gensim;
PGPASSWORD=$TM_SENTINEL_SQL_ROOT_PASSWORD;

cat '$TM_BASE_PATH/util/pericog.sql' |
sed 's/\$PW_PERICOG/'$(cat /srv/auth/sql/pericog.pw)'/g' |
psql -e -h $TM_PERICOG_ADDRESS -U postgres thisminute;
