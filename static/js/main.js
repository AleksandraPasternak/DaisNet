$(document).ready(function () {
	
    // Init
    $('.image-section').hide();
    $('.gradcam-section').hide();
    $('.loader').hide();
    $('#result').hide();
    var uploadFileName;

    blurFunction = function(state, res) {
    /* state can be 1 or 0 */
        //var containerElement = document.getElementsByTagName("BODY")[0];
        var containerElement = document.getElementById('main-page');
        var overlayEle = document.getElementById('page-overlay');

        if (state) {
            //$('#popup').css('background-image', 'url(' + res + ')');
            overlayEle.style.display = 'block';
            containerElement.setAttribute('class', 'blur');
        } else {
            overlayEle.style.display = 'none';
            containerElement.setAttribute('class', null);
        }
    };

  var crop_canvas = null;

  var resizeableImage = function(image_target) {
    // Some variable and settings
    var $container,
    orig_src = new Image(),
    image_target = $(image_target).get(0),
    event_state = {},
    constrain = false,
    min_width = 60, // Change as required
    min_height = 60,
    max_width = 800, // Change as required
    max_height = 1900,
    resize_canvas = document.createElement('canvas');
    imageData=null;

    init = function(){
    
    //load a file with html5 file api
    $("#imageUpload").change(function(evt) {
          $('.image-section').show();
          $('#btn-predict').show();
          $('#result').text('');
          $('#result').hide();
          $('.gradcam-section').hide();
      
      var files = evt.target.files; // FileList object
      var reader = new FileReader();

      reader.onload = function(e) {
        blurFunction(1, e.target.result);
        $('#imagePreview').css('background-image', 'url(' + e.target.result + ')');
        $('#imagePreview').hide();
        $('#imagePreview').fadeIn(650); //ladnie sie pojawia
        imageData=reader.result;
        loadData();
      }
      reader.readAsDataURL(files[0]);
      uploadFileName = evt.target.value;

      evt.target.value = ''
    });

      // When resizing, we will always use this copy of the original as the base
      orig_src.src=image_target.src;

      // Wrap the image with the container and add resize handles
      $(image_target)
      .wrap('<div class="resize-container"></div>')
      .before('<span class="resize-handle resize-handle-nw"></span>')
      .before('<span class="resize-handle resize-handle-ne"></span>')
      .after('<span class="resize-handle resize-handle-se"></span>')
      .after('<span class="resize-handle resize-handle-sw"></span>');

      // Assign the container to a variable
      $container =  $('.resize-container');

    $container.prepend('<div class="resize-container-ontop"></div>');
    
      // Add events
      $container.on('mousedown touchstart', '.resize-handle', startResize);
      $container.on('mousedown touchstart', '.resize-container-ontop', startMoving);
      $('.crop').on('click', crop);
    };
    
    loadData = function() {
        
    //set the image target
    image_target.src=imageData;
    orig_src.src=image_target.src;

    $(image_target).css({
      width:'auto',
      height:'auto'
    });
    
    //resize the canvas
    $(orig_src).bind('load',function() {
      resizeImageCanvas($(image_target).width(),$(image_target).height());
    });
    };
    
    startResize = function(e){
      e.preventDefault();
      e.stopPropagation();
      saveEventState(e);
      $(document).on('mousemove touchmove', resizing);
      $(document).on('mouseup touchend', endResize);
    };

    endResize = function(e){
    resizeImageCanvas($(image_target).width(), $(image_target).height())
      e.preventDefault();
      $(document).off('mouseup touchend', endResize);
      $(document).off('mousemove touchmove', resizing);
    };

    saveEventState = function(e){
      // Save the initial event details and container state
      event_state.container_width = $container.width();
      event_state.container_height = $container.height();
      event_state.container_left = $container.offset().left; 
      event_state.container_top = $container.offset().top;
      event_state.mouse_x = (e.clientX || e.pageX || e.originalEvent.touches[0].clientX) + $(window).scrollLeft(); 
      event_state.mouse_y = (e.clientY || e.pageY || e.originalEvent.touches[0].clientY) + $(window).scrollTop();
    
    // This is a fix for mobile safari
    // For some reason it does not allow a direct copy of the touches property
    if(typeof e.originalEvent.touches !== 'undefined'){
      event_state.touches = [];
      $.each(e.originalEvent.touches, function(i, ob){
        event_state.touches[i] = {};
        event_state.touches[i].clientX = 0+ob.clientX;
        event_state.touches[i].clientY = 0+ob.clientY;
      });
    }
      event_state.evnt = e;
    };

    resizing = function(e){
      var mouse={},width,height,left,top,offset=$container.offset();
      mouse.x = (e.clientX || e.pageX || e.originalEvent.touches[0].clientX) + $(window).scrollLeft(); 
      mouse.y = (e.clientY || e.pageY || e.originalEvent.touches[0].clientY) + $(window).scrollTop();
      
      // Position image differently depending on the corner dragged and constraints
      if( $(event_state.evnt.target).hasClass('resize-handle-se') ){
        width = mouse.x - event_state.container_left;
        height = mouse.y  - event_state.container_top;
        left = event_state.container_left;
        top = event_state.container_top;
      } else if($(event_state.evnt.target).hasClass('resize-handle-sw') ){
        width = event_state.container_width - (mouse.x - event_state.container_left);
        height = mouse.y  - event_state.container_top;
        left = mouse.x;
        top = event_state.container_top;
      } else if($(event_state.evnt.target).hasClass('resize-handle-nw') ){
        width = event_state.container_width - (mouse.x - event_state.container_left);
        height = event_state.container_height - (mouse.y - event_state.container_top);
        left = mouse.x;
        top = mouse.y;
        if(constrain || e.shiftKey){
          top = mouse.y - ((width / orig_src.width * orig_src.height) - height);
        }
      } else if($(event_state.evnt.target).hasClass('resize-handle-ne') ){
        width = mouse.x - event_state.container_left;
        height = event_state.container_height - (mouse.y - event_state.container_top);
        left = event_state.container_left;
        top = mouse.y;
        if(constrain || e.shiftKey){
          top = mouse.y - ((width / orig_src.width * orig_src.height) - height);
        }
      }
    
      // Optionally maintain aspect ratio
      if(constrain || e.shiftKey){
        height = width / orig_src.width * orig_src.height;
      }

      if(width > min_width && height > min_height && width < max_width && height < max_height){
        // To improve performance you might limit how often resizeImage() is called
        resizeImage(width, height);  
        // Without this Firefox will not re-calculate the the image dimensions until drag end
        $container.offset({'left': left, 'top': top});
      }
    }

    resizeImage = function(width, height){
    $(image_target).width(width).height(height);
    };
    
    resizeImageCanvas = function(width, height){
      resize_canvas.width = width;
      resize_canvas.height = height;
      resize_canvas.getContext('2d').drawImage(orig_src, 0, 0, width, height);   
      $(image_target).attr('src', resize_canvas.toDataURL("image/jpg"));
    //$(image_target).width(width).height(height);
    };

    startMoving = function(e){
      e.preventDefault();
      e.stopPropagation();
      saveEventState(e);
      $(document).on('mousemove touchmove', moving);
      $(document).on('mouseup touchend', endMoving);
    };

    endMoving = function(e){
      e.preventDefault();
      $(document).off('mouseup touchend', endMoving);
      $(document).off('mousemove touchmove', moving);
    };

    moving = function(e){
      var  mouse={}, touches;
      e.preventDefault();
      e.stopPropagation();
      
      touches = e.originalEvent.touches;
      
      mouse.x = (e.clientX || e.pageX || touches[0].clientX) + $(window).scrollLeft(); 
      mouse.y = (e.clientY || e.pageY || touches[0].clientY) + $(window).scrollTop();
      $container.offset({
        'left': mouse.x - ( event_state.mouse_x - event_state.container_left ),
        'top': mouse.y - ( event_state.mouse_y - event_state.container_top ) 
      });
      // Watch for pinch zoom gesture while moving
      if(event_state.touches && event_state.touches.length > 1 && touches.length > 1){
        var width = event_state.container_width, height = event_state.container_height;
        var a = event_state.touches[0].clientX - event_state.touches[1].clientX;
        a = a * a; 
        var b = event_state.touches[0].clientY - event_state.touches[1].clientY;
        b = b * b; 
        var dist1 = Math.sqrt( a + b );
        
        a = e.originalEvent.touches[0].clientX - touches[1].clientX;
        a = a * a; 
        b = e.originalEvent.touches[0].clientY - touches[1].clientY;
        b = b * b; 
        var dist2 = Math.sqrt( a + b );

        var ratio = dist2 /dist1;

        width = width * ratio;
        height = height * ratio;
        // To improve performance you might limit how often resizeImage() is called
        resizeImage(width, height);
      }
    };

    crop = function(){
      //Find the part of the image that is inside the crop box
      var left = $('.overlay').offset().left- $container.offset().left,
          top =  $('.overlay').offset().top - $container.offset().top,
          width = $('.overlay').width(),
          height = $('.overlay').height();
      
      crop_canvas = document.createElement('canvas');
    
      crop_canvas.width = width;
      crop_canvas.height = height;
    
      crop_canvas.getContext('2d').drawImage(image_target, left, top, width, height, 0, 0, width, height);

    var dataURL=crop_canvas.toDataURL("image/jpg");
    image_target.src=dataURL;
    orig_src.src=image_target.src;
    $('#imagePreview').hide();
    $('#imagePreview').fadeIn(650);
    $('#imagePreview').css('background-image', 'url(' + dataURL + ')');
    
    
    $(image_target).bind("load",function() {
      $(this).css({
        width:width,
        height:height
      }).unbind('load').parent().css({
        top:$('.overlay').offset().top- $('.crop-wrapper').offset().top,
        left:$('.overlay').offset().left- $('.crop-wrapper').offset().left
      })
    });
      //window.open(crop_canvas.toDataURL("image/jpg"));
    }

    init();
  };

  // Kick everything off with the target image
  resizeableImage($('.resize-image'));

  $('.crop').click(function() {
        blurFunction(0, 0);
  });

    // Predict
    $('#btn-predict').click(function () {
        crop_canvas.toBlob(function (blob) {
            var form_data = new FormData();
            form_data.append('file', blob, uploadFileName)

            // Show loading animation
            $(this).hide();
            $('#loader1').show();

            // Make prediction by calling api /predict
            $.ajax({
                type: 'POST',
                url: '/predict',
                data: form_data,
                contentType: false,
                cache: false,
                processData: false,
                async: true,
                success: function (data) {
                    // Get and display the result
                    $('#loader1').hide();
                    $('#result').fadeIn(600);
                    if (data.true_class == "") $('#result').text(' Result: ' + data.result + data.probabilities);
                    else $('#result').text(' True class: ' + data.true_class + '\n' + ' Result: ' + data.result + data.probabilities);
                    if (data.result == 'no corrosion') {
                        $('#result').css('color', '#80b918');
                    } else {
                        $('#result').css('color', '#dc2f02');
                    }
                    $('.gradcam-section').show();
                    $('.gradcam-preview').hide();
                    $('#btn-gradcam').show();
                    console.log('Success!');
                }
            });
        }, 'image/jpg');
    });

    // gradCam
    $('#btn-gradcam').click(function () {

        crop_canvas.toBlob(function (blob) {

            var form_data = new FormData();
            form_data.append('file', blob, 'image.jpg')

            // Show loading animation
            $(this).hide();
            $('#loader2').show();

            // Make prediction by calling api /predict
            $.ajax({
                type: 'POST',
                url: '/gradcam',
                data: form_data,
                contentType: false,
                cache: false,
                processData: false,
                async: true,
                success: function (data) {
                    $('#loader2').hide();
                    $('.gradcam-preview').show();
                    $("#gradcamOutput").attr("src", "data:image/jpg;base64," + data);
                    console.log('Success!');
                }
            });
        }, 'image/jpg');
    });

    var previous=0;
    $('#gradcamOutput').click(function() {
        var s = '#gradcamOutput'
        if($(s).width() == 320) {
            $(s).animate({'width':'640px'});
            $(s).css({'cursor':'zoom-out'});
            $('.gradcam-preview').css({'height':'1100px'})
        }
        else if($(previous).width() != 320) {
            $('.gradcam-preview').css({'height':'550px'})
            $(previous).animate({'width':'320px'});
            $(previous).css({'cursor':'zoom-in'});
        }
    previous=s;
    });

});
