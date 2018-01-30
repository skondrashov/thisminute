import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import { fetchNewTweet } from '../actions/index';

class TweetList extends Component {
  constructor(props) {
    super(props);

    this.state = {
      tweetListTweets: [
        {username: "user1", content: "content1", tweet_id: "1"},
        {username: "user2", content: "content2", tweet_id: "2"},
        {username: "user3", content: "content3", tweet_id: "3"},
        {username: "user4", content: "content4", tweet_id: "4"},
        {username: "user5", content: "content5", tweet_id: "5"}
      ]
    }
  }

  renderTweetBlocks() {
    return this.state.tweetListTweets.map((tweet) => {
      return <TweetBlock key={tweet.tweet_id} tweet={tweet} />;
    });
  }

  render() {
    return (
      <div className="tweet-list">
        {this.renderTweetBlocks()}
      </div>
    );
  }
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators({ fetchNewTweet }, dispatch);
}

function mapStateToProps(state) {
  return { tweetListTweets : state.tweetListTweets };
}

TweetList = connect(mapStateToProps, mapDispatchToProps)(TweetList);
export default TweetList;
