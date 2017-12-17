import React, { Component } from 'react';
import TweetBlock from './TweetBlock';

class CategoryBlock extends Component {
  render() {
    return (
      <div className="col-xs-4 category-list">
        <div className="row text-center">
          <h3>Category Name</h3>
        </div>
        <div className="row">
          <TweetBlock />
        </div>
        <div className="row">
          <TweetBlock />
        </div>
      </div>
    );
  }
}

export default CategoryBlock;
