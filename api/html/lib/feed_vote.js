class FeedVote extends HTMLElement {

	connectedCallback() {
		$(this)
			.html(`
				<div class="up"></div>
				<div class="down"></div>
			`
			.children()
				.click(e => {
					var $element = $(e.target);

					var data = {
						id: $element.closest('.tweet').attr('id').split("_")[1]
					};

					sentiments.values.forEach(sentiment => {
						if (element.parent().hasClass(sentiment)) {
							data[sentiment] = element.hasClass('up');
						}
					});

					$.ajax({
						url: "/api/vote",
						method: "POST",
						data: data,
					}).done(function(data) {
						if (data != 'success') {
							return;
						}
						element.siblings().removeClass('voted');
						element.addClass('voted');
					});
				}
		;
	}
}

customElements.define('feed-vote', FeedVote);
