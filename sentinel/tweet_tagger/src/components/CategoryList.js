import React, { Component } from 'react';
import CategoryBlock from './CategoryBlock';

class CategoryList extends Component {
  constructor(props) {
    super(props);

    this.state = {
      categories: [
        { categoryName: "Not Relevant", categoryId: 0, tweets: []},
        { categoryName: "Thoughts/Prayers", categoryId: 1, tweets: []},
        { categoryName: "Eyewitness", categoryId: 2, tweets: []}
      ]
    }
  }

  _removeTweetFromCategory(tweetId, categoryId) {
    let newState = this.state.categories;
    newState.forEach((category) =>{
      if(category.categoryId === categoryId) {
        category.tweets = category.tweets.filter(e => e.id !== tweetId);
      }
    });
    this.setState({ categories: newState });
  }

  _addTweetToCategory(tweet, categoryId) {
    let newState = this.state.categories;
    newState.forEach((category) => {
      if(category.categoryId === categoryId) {
        if(!category.tweets.find(e => e.id === tweet.tweet.id)) {
          category.tweets.push(tweet.tweet);
        }
      }
    });
    this.setState({ categories: newState });
  }

  renderCategoryBlocks() {
    return this.state.categories.map((category) => {
      return (
        <CategoryBlock
          key={category.categoryId}
          categoryName={category.categoryName}
          categoryId={category.categoryId}
          tweets={category.tweets}
          _addTweetToCategory={(tweet, categoryId) => this._addTweetToCategory(tweet, categoryId)}
          _removeTweetFromCategory={(tweetId, categoryId) => this._removeTweetFromCategory(tweetId, categoryId)}
        />
      );
    });
  }

  render() {
    return (
      <div className="category-block">
        {this.renderCategoryBlocks()}
      </div>
    );
  }
}

export default CategoryList;
