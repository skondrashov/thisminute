/* globals tm */
import React, {Component} from 'react';
import './css/sidebar.scss';
import $ from 'jquery';

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

		$(document).keypress(e => {
			if (e.which === 118) {
				if (vote_mode) {
					$(`.vote-only`).addClass('hidden');
					vote_mode = false;
					this.poll();
				} else {
					$(`.vote-only`).removeClass('hidden');
					vote_mode = true;
				}
			}
		});

		this.poll();
	}

	render() {
		return (
			<div className="sidebar">
				<div className="infobox vote-only hidden">
					<div className="count">{this.state.count}</div>
					<div className="description">{this.state.description}</div>
				</div>
				{this.state.markers}
			</div>
		);
	}

	poll = () => {
		$.ajax({
			url: "/api/markers"
		}).done(data => {
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
