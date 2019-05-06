/* globals tm */
import React, {Component} from 'react';
import './css/sidebar.scss';

import Tweet from './tweet';

let vote_mode = false;

export default class Sidebar extends Component {
	constructor(props) {
		super(props);

		this.state = {
			count: 0,
			markers: [],
		};

		tm.setDescription = (description) => this.setState({description});

		document.addEventListener("keypress", e => {
			if (e.which === 118) {
				const elements = [...document.getElementsByClassName('vote-only')];
				if (vote_mode) {
					elements.forEach(element => element.classList.remove('show'));
					vote_mode = false;
					this.poll();
				} else {
					elements.forEach(element => element.classList.add('show'));
					vote_mode = true;
				}
			}
		}, false);

		this.poll();
	}

	render() {
		return (
			<div className="sidebar">
				<div className="infobox vote-only">
					<div className="count">{this.state.count}</div>
					<div className="description">{this.state.description}</div>
				</div>
				{this.state.markers}
			</div>
		);
	}

	poll = () => {
		fetch("/api/markers").then(response => response.json())
			.then(data => {
				const markers = data.tweets.map(tweet =>
					<Tweet
							key={tweet.id}
							id={tweet.id}
							lng={tweet.lon}
							lat={tweet.lat}
							text={tweet.text}
						/>
					);

				this.setState({
					count: data.count,
					markers: markers,
				});
			});

		if (!vote_mode) {
			setTimeout(this.poll, 800);
		}
	}
}
