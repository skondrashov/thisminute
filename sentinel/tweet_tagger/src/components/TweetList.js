import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import axios from 'axios';

const MAX_QUEUE_SIZE = 30;
const LOW_QUEUE_AMOUNT = 6;
const MAX_TWEETLIST_SIZE = 5;
const GET_NEW_TWEET_INTERVAL = 10000;

class TweetList extends Component {
  constructor(props) {
    super(props);

    this.state = { tweets: [] };
  }

  componentDidMount(){
    this.getTweetTimer = setInterval(
      () => this._refillTweetList(),
      GET_NEW_TWEET_INTERVAL
    );
    this._refillTweetList();
  }

  _refillTweetList() {
    if(this.state.tweets.length <= LOW_QUEUE_AMOUNT) {
      let n = MAX_QUEUE_SIZE - this.state.tweets.length;
      const url = `http://thisminute.org/sentinel/get_tweet.php?n=${n}`;

      axios.get(url)
        .then((response) => {
          var newTweets = [];
          for(var tweet of response.data) {
            let newTweet = { id: Math.random(), content: tweet };
            newTweets.push(newTweet);
          }
          this.setState({ tweets: this.state.tweets.concat(newTweets) });
        })
    }
  }

  componentWillUnmount() {
    clearInterval(this.getTweetTimer);
  }

  // TODO: Use a better search algo to find the element to remove
  // could keep array sorted by ID and use binary search
  _removeFromTweetList(tweet) {
    this.setState({ tweets: this.state.tweets.filter(e => e.id !== tweet.tweet.id) });
  }

  _renderTweetBlocks(tweetArray) {
    return this.state.tweets.map((tweet, i) => {
      if(i >= MAX_TWEETLIST_SIZE) {
        return;
      }
      return(
        <TweetBlock
          tweet={tweet}
          key={i}
          _removeFromTweetList={tweet => this._removeFromTweetList(tweet)}
        />
      );
    });
  }

  render() {
    return (
      <div className="tweet-list">
        {this._renderTweetBlocks()}
      </div>
    );
  }
}

export default TweetList;
