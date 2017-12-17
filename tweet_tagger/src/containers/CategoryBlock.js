import React, { Component } from 'react';
import TweetBlock from './TweetBlock';

class CategoryBlock extends Component {
  render() {
    return (
      <div className="grid category-list">
        <div className="text-center">
          <h3>Category Name</h3>
        </div>
        <div className="">
          <TweetBlock />
        </div>
        <div className="">
          <TweetBlock />
        </div>
      </div>
    );
  }
}

export default CategoryBlock;
