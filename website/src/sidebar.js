/* globals tm */
import React, {Component} from 'react';
import './css/sidebar.scss';
import $ from 'jquery';

import Tweet from './tweet';

let vote_mode = false;

export default class Sidebar extends Component {
	constructor(props) {
		super(props);

		const sentiments = tm.sentiments.map((sentiment, i) => {
			return (
				<div key={sentiment.key} className={sentiment.key}>
					<div className="up hidden">{sentiment.up}</div>
					<div className="down hidden">{sentiment.down}</div>
				</div>
			)
		});

		this.state = {
			count: 0,
			sentiments: sentiments,
			markers: [],
		};

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

		$(document).on("click", ".x", () => {
			var element = $(this);
			$.ajax({
				url: "/api/vote",
				method: "POST",
				data: {
					id: element.closest('.tweet').attr('id').split("_")[1],
					submit: true
				}
			}).done(function(data) {
				this.poll();
			});
		});

		this.poll();
	}

	render() {
		return (
			<div className="sidebar">
				<div className="infobox vote-only hidden">
					<div className="count">{this.state.count}</div>
					<div className="description">
						{this.state.sentiments}
					</div>
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
