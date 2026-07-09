$(function() {

    $(document).ready(function(){
        $('ul.dropdown-menu [data-toggle=dropdown]').on('click', function(event) {
            event.preventDefault(); 
            event.stopPropagation(); 
            $(this).parent().siblings().removeClass('open');
            $(this).parent().toggleClass('open');
        });
    });

	
		
    $('#count_down1').countdown(cd1).on('update.countdown', function(event) {
      var $this = $(this).html(event.strftime(''
        + ' <div class="count_down_day"><h3 class="so_count_down" >%D</h3> &nbsp;:  <p class="chu_count_down" >Ngày</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%H</h3> &nbsp;:  <p class="chu_count_down" >Giờ</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%M</h3> &nbsp;:  <p class="chu_count_down" >Phút</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%S</h3>  <p class="chu_count_down" >Giây</p></div> '));
    });
	
	/*
    $('#count_down2').countdown(cd2).on('update.countdown', function(event) {
      var $this = $(this).html(event.strftime(''
        + ' <div class="count_down_day"><h3 class="so_count_down" >%D</h3> &nbsp;:  <p class="chu_count_down" >Ngày</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%H</h3> &nbsp;:  <p class="chu_count_down" >Giờ</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%M</h3> &nbsp;:  <p class="chu_count_down" >Phút</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%S</h3>  <p class="chu_count_down" >Giây</p></div> '));
    });
	
	*/
	
    $('#count_down3').countdown(cd3).on('update.countdown', function(event) {
      var $this = $(this).html(event.strftime(''
        + ' <div class="count_down_day"><h3 class="so_count_down" >%D</h3> &nbsp;:  <p class="chu_count_down" >Ngày</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%H</h3> &nbsp;:  <p class="chu_count_down" >Giờ</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%M</h3> &nbsp;:  <p class="chu_count_down" >Phút</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%S</h3>  <p class="chu_count_down" >Giây</p></div> '));
    });
	
	$('#count_down5').countdown(cd5).on('update.countdown', function(event) {
      var $this = $(this).html(event.strftime(''
        + ' <div class="count_down_day"><h3 class="so_count_down" >%D</h3> &nbsp;:  <p class="chu_count_down" >Ngày</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%H</h3> &nbsp;:  <p class="chu_count_down" >Giờ</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%M</h3> &nbsp;:  <p class="chu_count_down" >Phút</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%S</h3>  <p class="chu_count_down" >Giây</p></div> '));
    });

	$('#count_down7').countdown(cd7).on('update.countdown', function(event) {
      var $this = $(this).html(event.strftime(''
        + ' <div class="count_down_day"><h3 class="so_count_down" >%D</h3> &nbsp;:  <p class="chu_count_down" >Ngày</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%H</h3> &nbsp;:  <p class="chu_count_down" >Giờ</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%M</h3> &nbsp;:  <p class="chu_count_down" >Phút</p></div> '
        + ' <div class="count_down_day"><h3 class="so_count_down" >%S</h3>  <p class="chu_count_down" >Giây</p></div> '));
    });
	
    // When the user scrolls down 20px from the top of the document, show the button
    $(window).scroll(function(){

        if ($(this).scrollTop() > 800) {
            $('.btn_backtop').fadeIn();
        }
        else {
            $('.btn_backtop').fadeOut();
        }

    });

    // When the user clicks on the button, scroll to the top of the document
    $('.btn_backtop').click(function() {
        $('body,html').animate({
                scrollTop: 0
            }, 800);
            return false;
    })

    // When the user clicks on the button, scroll to the top of the document
    $('.btn_search').click(function() {
        $('.form-group').toggle('hidden_up992');
    })
});