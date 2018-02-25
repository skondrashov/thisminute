import React, { Component } from 'react';
import CategoryBlock from './CategoryBlock';

class CategoryList extends Component {
  constructor(props) {
    super(props);

    this.state = {
      categories: [
        { categoryName: "Eyewitness", categoryId: 0, tweets: []},
        { categoryName: "Secondhand Account", categoryId: 1, tweets: []},
        { categoryName: "Not Relevant", categoryId: 2, tweets: []},
      ]
    }
  }

  _addTweetToCategory(tweet, categoryId) {
    let newState = this.state.categories;
    newState.forEach((category) => {
      if(category.categoryId === categoryId) {
        category.tweets.push(tweet);
      }
    });
    this.setState({ categories: newState });
  }

  _removeTweetFromCategory(tweet, categoryId) {
    if(tweet.categoryId === categoryId) {
      return null;
    }
    let newState = this.state.categories;
    newState.forEach((category) => {
      if(category.categoryId === categoryId) {
        for(var i in category.tweets) {
          if(category.tweets[i].id === tweet.id) {
            break;
          }
        }
        category.tweets.splice(i, 1);
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
          _removeTweetFromCategory={(tweet, categoryId) => this._removeTweetFromCategory(tweet, categoryId)}
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
