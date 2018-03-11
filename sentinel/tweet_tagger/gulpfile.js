const gulp = require('gulp');
const less = require('gulp-less');

gulp.task('less-css', ()=>{
	gulp.src('./src/*.less')
		.pipe(less())
		.pipe(gulp.dest('./src/'))
})

gulp.task('watch', () =>{
	gulp.watch(['./src/*.less'], ['less-css']);
})

gulp.task('default', ['less-css', 'watch'])