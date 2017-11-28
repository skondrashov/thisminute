TM_BASE_PATH=~/thisminute
TM_KEY_PATH=~/thisminute/auth/ssl/tm.pem

tm_push() {
	rsync -uavz -e "ssh -i ${TM_KEY_PATH}" --chmod=777 --del --delete-excluded --exclude '*.git*' "$@"
}
tm_local_push() {
	rsync -uav --chmod=777 --del --delete-excluded --exclude '*.git*' "$@"
}

tm_generate_auth() {
	apg -a 1 -n 1 -c cl_seed -d -M ncl -m 32 > $TM_BASE_PATH/auth/mysql/sentinel.pw;
	apg -a 1 -n 1 -c cl_seed -d -M ncl -m 32 > $TM_BASE_PATH/auth/mysql/archivist.pw;
	apg -a 1 -n 1 -c cl_seed -d -M ncl -m 32 > $TM_BASE_PATH/auth/mysql/tweet2vec.pw;
	apg -a 1 -n 1 -c cl_seed -d -M ncl -m 32 > $TM_BASE_PATH/auth/mysql/pericog.pw;
}

sentinel() { ssh -i $TM_KEY_PATH $TM_SENTINEL_ADDRESS; }
sentinel_push() {
	tm_push $TM_BASE_PATH/config.ini $TM_SENTINEL_ADDRESS:/srv/config.ini;
	tm_push $TM_BASE_PATH/html/      $TM_SENTINEL_ADDRESS:/var/www/html/;
	tm_push $TM_BASE_PATH/auth/      $TM_SENTINEL_ADDRESS:/srv/auth/;
}

archivist() { ssh -i $TM_KEY_PATH $TM_ARCHIVIST_ADDRESS; }
archivist_push() {
	tm_push                 $TM_BASE_PATH/config.ini     $TM_ARCHIVIST_ADDRESS:/srv/config.ini;
	tm_push --exclude 'lib' $TM_BASE_PATH/archivist/     $TM_ARCHIVIST_ADDRESS:/srv/etc/;
	tm_push                 $TM_BASE_PATH/auth/          $TM_ARCHIVIST_ADDRESS:/srv/auth/;
	tm_push                 $TM_BASE_PATH/archivist/lib/ $TM_ARCHIVIST_ADDRESS:/srv/lib/;
}

pericog() { ssh -i $TM_KEY_PATH $TM_PERICOG_ADDRESS; }
pericog_push() {
	if [ $TM_PERICOG_ADDRESS == "localhost" ]
	then
		tm_local_push                 $TM_BASE_PATH/config.ini                      /srv/config.ini;
		tm_local_push --exclude 'lib' $TM_BASE_PATH/pericog/                        /srv/etc/;
		tm_local_push                 $TM_BASE_PATH/auth/                           /srv/auth/;
		tm_local_push                 $TM_BASE_PATH/lib/ $TM_BASE_PATH/pericog/lib/ /srv/lib/;
	else
		tm_push                 $TM_BASE_PATH/config.ini                      $TM_PERICOG_ADDRESS:/srv/config.ini;
		tm_push --exclude 'lib' $TM_BASE_PATH/pericog/                        $TM_PERICOG_ADDRESS:/srv/etc/;
		tm_push                 $TM_BASE_PATH/auth/                           $TM_PERICOG_ADDRESS:/srv/auth/;
		tm_push                 $TM_BASE_PATH/lib/ $TM_BASE_PATH/pericog/lib/ $TM_PERICOG_ADDRESS:/srv/lib/;
	fi
}
pericog_db_init() {
	if [ $TM_PERICOG_ADDRESS == "localhost" ]
	then
		cat "$TM_BASE_PATH/util/pericog.sql" |
		sed "s/\$PW_TWEET2VEC/"$( cat $TM_BASE_PATH/auth/mysql/tweet2vec.pw )"/g" |
		sed "s/\$PW_PERICOG/"$(   cat $TM_BASE_PATH/auth/mysql/pericog.pw   )"/g" |
		sudo mysql -u root -p$TM_MYSQL_ROOT_PASSWORD;
	else
		cat "$TM_BASE_PATH/util/pericog.sql" |
		sed "s/\$PW_TWEET2VEC/"$( cat $TM_BASE_PATH/auth/mysql/tweet2vec.pw )"/g" |
		sed "s/\$PW_PERICOG/"$(   cat $TM_BASE_PATH/auth/mysql/pericog.pw   )"/g" |
		ssh -i $TM_KEY_PATH $TM_PERICOG_ADDRESS "sudo mysql -u root -p$TM_MYSQL_ROOT_PASSWORD";
	fi
}
pericog_init() {
	pericog_db_init;
	pericog_push;
}

tweets_usa() {
	mysql -u root -p -h tweets-usa.thisminute.org \
		--ssl-ca=$TM_BASE_PATH/auth/ssl/tweets-usa/server-ca.pem \
		--ssl-cert=$TM_BASE_PATH/auth/ssl/tweets-usa/client-cert.pem \
		--ssl-key=$TM_BASE_PATH/auth/ssl/tweets-usa/client-key.pem;
}
tweets_usa_db_init() {
	cat "$TM_BASE_PATH/util/tweets.sql" |
	sed "s/\$PW_SENTINEL/"$(  cat $TM_BASE_PATH/auth/mysql/sentinel.pw  )"/g" |
	sed "s/\$PW_ARCHIVIST/"$( cat $TM_BASE_PATH/auth/mysql/archivist.pw )"/g" |
	sed "s/\$PW_TWEET2VEC/"$( cat $TM_BASE_PATH/auth/mysql/tweet2vec.pw )"/g" |
	sed "s/\$PW_PERICOG/"$(   cat $TM_BASE_PATH/auth/mysql/pericog.pw   )"/g" |

	mysql -v -u root -p -h tweets-usa.thisminute.org \
		--ssl-ca=$TM_BASE_PATH/auth/ssl/tweets-usa/server-ca.pem \
		--ssl-cert=$TM_BASE_PATH/auth/ssl/tweets-usa/client-cert.pem \
		--ssl-key=$TM_BASE_PATH/auth/ssl/tweets-usa/client-key.pem;
}
