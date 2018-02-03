import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import { fetchNewTweet } from '../actions/index';

class TweetList extends Component {
  renderTweetBlocks(tweetArray) {
    if(this.props.tweetListTweets) {
      return this.props.tweetListTweets.map((tweet) => {
        return <TweetBlock key={tweet.tweet_id} tweet={tweet} />;
      });
    }
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
  return { tweetListTweets: state.TweetListReducer.tweetListTweets };
}

TweetList = connect(mapStateToProps, mapDispatchToProps)(TweetList);
export default TweetList;
