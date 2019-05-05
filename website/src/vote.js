/* globals tm */
import React from 'react';

export default (props) =>
<div className="vote vote-only hidden">
	<div
		className="up"
		onMouseOver={() => tm.setDescription(props.sentiment.up)}
		onMouseOut={() => tm.setDescription('')}
		onClick={() => props.vote(props.sentiment.key, true)}
	></div>
	<div
		className="down"
		onMouseOver={() => tm.setDescription(props.sentiment.down)}
		onMouseOut={() => tm.setDescription('')}
		onClick={() => props.vote(props.sentiment.key, false)}
	></div>
</div>
