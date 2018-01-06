TM_BASE_PATH=~/thisminute
TM_KEY_PATH=~/thisminute/auth/ssl/tm.pem

tm_push() {
    rsync -uavz -e "ssh -i ${TM_KEY_PATH}" --del --delete-excluded --exclude '*.git*' "$@"
}
tm_local_push() {
    rsync -uav --chmod=777 --del --delete-excluded --exclude '*.git*' "$@"
}
tm_connect() {
    echo "Connecting to $1"
    ssh -i $TM_KEY_PATH $1;
}

tm_generate_auth() {
    apg -a 1 -n 1 -c cl_seed -d -M ncl -m 32 > $TM_BASE_PATH/auth/sql/sentinel.pw;
    apg -a 1 -n 1 -c cl_seed -d -M ncl -m 32 > $TM_BASE_PATH/auth/sql/archivist.pw;
    apg -a 1 -n 1 -c cl_seed -d -M ncl -m 32 > $TM_BASE_PATH/auth/sql/pericog.pw;
}

archivist() {
    tm_connect $TM_ARCHIVIST_ADDRESS;
}
archivist_push() {
    echo "writing /srv/config.ini"; tm_push                 $TM_BASE_PATH/config.ini     $TM_ARCHIVIST_ADDRESS:/srv/config.ini;
    echo "writing /srv/etc/";       tm_push --exclude 'lib' $TM_BASE_PATH/archivist/     $TM_ARCHIVIST_ADDRESS:/srv/etc/;
    echo "writing /srv/auth/";      tm_push                 $TM_BASE_PATH/auth/          $TM_ARCHIVIST_ADDRESS:/srv/auth/;
    echo "writing /srv/lib/";       tm_push                 $TM_BASE_PATH/archivist/lib/ $TM_ARCHIVIST_ADDRESS:/srv/lib/;
}
archivist_init() {
    # edit php.ini to include /srv/lib
    # copy service to /etc/systemd/system/archivist.service

    local SCRIPT="
            cd;
            sudo chmod -R 777 /srv;
            sudo apt-get install rsync php php-pgsql;
        ";
    if [ $TM_ARCHIVIST_ADDRESS == "localhost" ]
    then
        eval $SCRIPT
    else
        ssh -i $TM_KEY_PATH $TM_ARCHIVIST_ADDRESS "$SCRIPT";
    fi

    archivist_push;
}

pericog() {
    tm_connect $TM_PERICOG_ADDRESS;
}
pericog_push() {
    if [ $TM_PERICOG_ADDRESS == "localhost" ]
    then
        echo "writing /srv/config.ini"; tm_local_push                 $TM_BASE_PATH/config.ini                      /srv/config.ini;
        echo "writing /srv/etc/";       tm_local_push --exclude 'lib' $TM_BASE_PATH/pericog/                        /srv/etc/;
        echo "writing /srv/auth/";      tm_local_push                 $TM_BASE_PATH/auth/                           /srv/auth/;
        echo "writing /srv/lib/";       tm_local_push                 $TM_BASE_PATH/lib/ $TM_BASE_PATH/pericog/lib/ /srv/lib/;
    else
        echo "writing /srv/config.ini"; tm_push                 $TM_BASE_PATH/config.ini                      $TM_PERICOG_ADDRESS:/srv/config.ini;
        echo "writing /srv/etc/";       tm_push --exclude 'lib' $TM_BASE_PATH/pericog/                        $TM_PERICOG_ADDRESS:/srv/etc/;
        echo "writing /srv/auth/";      tm_push                 $TM_BASE_PATH/auth/                           $TM_PERICOG_ADDRESS:/srv/auth/;
        echo "writing /srv/lib/";       tm_push                 $TM_BASE_PATH/lib/ $TM_BASE_PATH/pericog/lib/ $TM_PERICOG_ADDRESS:/srv/lib/;
    fi
}
pericog_init() {
    local SCRIPT="
            cd;
            sudo chmod -R 777 /srv;
            wget http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/cuda-repo-ubuntu1604_9.0.176-1_amd64.deb;
            sudo dpkg -i cuda-repo-ubuntu1604_9.0.176-1_amd64.deb;
            rm cuda-repo-ubuntu1604_9.0.176-1_amd64.deb;
            sudo apt-key adv --fetch-keys http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/7fa2af80.pub;
            sudo apt-get update;
            sudo apt-get -y install postgresql postgis cuda;
            pip install --upgrade pip;
            sudo pip install numpy scipy unidecode;
            sudo pip install gensim;
            cat '$TM_BASE_PATH/util/pericog.sql' |
            sed 's/\$PW_PERICOG/'$(cat $TM_BASE_PATH/auth/sql/pericog.pw)'/g' |
            sudo -u postgres psql -e;
        ";
    if [ $TM_PERICOG_ADDRESS == "localhost" ]
    then
        eval $SCRIPT
    else
        ssh -i $TM_KEY_PATH $TM_PERICOG_ADDRESS "$SCRIPT";
    fi

    pericog_push;
}

sentinel() {
    tm_connect $TM_SENTINEL_ADDRESS;
}
sentinel_push() {
    echo "writing /srv/config.ini"; tm_push $TM_BASE_PATH/config.ini $TM_SENTINEL_ADDRESS:/srv/config.ini;
    echo "writing /var/www/html/";  tm_push $TM_BASE_PATH/html/      $TM_SENTINEL_ADDRESS:/var/www/html/;
    echo "writing /srv/auth/";      tm_push $TM_BASE_PATH/auth/      $TM_SENTINEL_ADDRESS:/srv/auth/;
}
sentinel_init() {
    local SCRIPT="
            cd;
            sudo chmod -R 777 /var/www;
            sudo chmod -R 777 /srv;
            sudo apt-get install rsync php php-pgsql;
        ";
    if [ $TM_SENTINEL_ADDRESS == "localhost" ]
    then
        eval $SCRIPT
    else
        ssh -i $TM_KEY_PATH $TM_SENTINEL_ADDRESS "$SCRIPT";
    fi

    sentinel_push;
}

tm_tweets() {
    if [ "$1" ]
    then
        local SUBSERVER="-$1"
    fi
    local HOST="tweets$SUBSERVER.thisminute.org"

    echo "Connecting to $HOST"
    psql -h $HOST -U postgres thisminute;
     #    --ssl-ca=$TM_BASE_PATH/auth/ssl/tweets/server-ca.pem \
     #    --ssl-cert=$TM_BASE_PATH/auth/ssl/tweets/client-cert.pem \
     #    --ssl-key=$TM_BASE_PATH/auth/ssl/tweets/client-key.pem;
}
tm_tweets_init() {
    if [ "$1" ]
    then
        local SUBSERVER="-$1"
    fi
    local HOST="tweets$SUBSERVER.thisminute.org"

    echo "Connecting to $HOST"
    cat "$TM_BASE_PATH/util/tweets.sql" |
    sed "s/\$PW_SENTINEL/"$(  cat $TM_BASE_PATH/auth/sql/sentinel.pw  )"/g" |
    sed "s/\$PW_ARCHIVIST/"$( cat $TM_BASE_PATH/auth/sql/archivist.pw )"/g" |
    sed "s/\$PW_PERICOG/"$(   cat $TM_BASE_PATH/auth/sql/pericog.pw   )"/g" |

    psql -e -h $HOST -U postgres thisminute;
     #    --ssl-ca=$TM_BASE_PATH/auth/ssl/tweets/server-ca.pem \
     #    --ssl-cert=$TM_BASE_PATH/auth/ssl/tweets/client-cert.pem \
     #    --ssl-key=$TM_BASE_PATH/auth/ssl/tweets/client-key.pem;
}
