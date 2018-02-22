This project was bootstrapped with [Create React App](https://github.com/facebookincubator/create-react-app).

## Prereqs
```
sudo apt-get install curl;\
curl -sL https://deb.nodesource.com/setup_9.x | sudo -E bash -;\
sudo apt-get install -y nodejs;\
sudo npm install --global gulp
```
You may see warnings about optional dependency fsevents. Those are normal.

## How To Build
```
cd ~/thisminute/sentinel/tweet_tagger;\
npm install;\
gulp less-css;\
npm start
```
If you have something running on localhost:3000 check your terminal and hit Y to run the site on localhost:3001

## How to Gulp
Right now the gulp file only compiles the less to css for us with webpack doing the live reloading of the page. You can run **gulp** in your terminal to watch for any changes to the less file. Every time the less is saved it will make a new CSS file.
