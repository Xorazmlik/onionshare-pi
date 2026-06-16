$(function () {
  var flash = function (category, message) {
    $('#flashes').append($('<li>').addClass(category).text(message));
  };
  var scriptSrc = document.getElementById('receive-script').src;
  var staticImgPath = scriptSrc.substr(0, scriptSrc.lastIndexOf('/') + 1).replace('js', 'img');
  $('#send').submit(function (event) {
    event.preventDefault();
    var formData = new FormData();
    var filenames = [];
    var $fileSelect = $('#file-select');
    if ($fileSelect.length > 0) {
      var files = $fileSelect.get(0).files;
      for (var i = 0; i < files.length; i++) {
        var file = files[i];
        filenames.push(file.name);
        formData.append('file[]', file, file.name);
      }
    }
    var $text = $('#text');
    if ($text.length > 0) {
      formData.append('text', $text.val());
    }
    $('#send').get(0).reset();
    var ajax = new XMLHttpRequest();
    ajax.upload.addEventListener('progress', function (event) {
      if (event.lengthComputable) {
        $('progress', ajax.$upload_div).attr({
          value: event.loaded,
          max: event.total,
        });
      }
      if (event.loaded == event.total) {
        $('.cancel', ajax.$upload_div).remove();
        $('.upload-status', ajax.$upload_div).text('Ma\'lumotlar Tor tarmog\'ini kesib o\'tishini kutmoqda...');
      }
    }, false);
    ajax.addEventListener('load', function (event) {
      ajax.$upload_div.remove();
      try {
        var response = JSON.parse(ajax.response);
        if ('new_body' in response) {
          $('body').html(response['new_body']);
          return;
        }
        if ('error_flashes' in response) {
          for (var i = 0; i < response['error_flashes'].length; i++) {
            flash('error', response['error_flashes'][i]);
          }
        }
        if ('info_flashes' in response) {
          for (var i = 0; i < response['info_flashes'].length; i++) {
            flash('info', response['info_flashes'][i]);
          }
        }
      } catch (e) {
        flash('error', 'Serverdan noto\'g\'ri javob: ' + ajax.response);
      }
    }, false);
    ajax.addEventListener('error', function (event) {
      flash('error', 'Yuklashda xatolik: ' + filenames.join(', '));
      ajax.$upload_div.remove();
    }, false);
    ajax.addEventListener('abort', function (event) {
      flash('error', 'Yuklash bekor qilindi: ' + filenames.join(', '));
    }, false);
    var $progress = $('<progress>').attr({ value: '0', max: 100 });
    var $cancel_button = $('<input>').addClass('cancel').attr({ type: 'button', value: 'Bekor qilish' });
    var $upload_filename = $('<div>').addClass('upload-filename').text(filenames.join(', '));
    var $upload_status = $('<div>').addClass('upload-status').text('Birinchi Tor tuguniga ma\'lumot yuborilmoqda...');
    var $upload_div = $('<div>')
      .addClass('upload')
      .append(
        $('<div>').addClass('upload-meta')
          .append($cancel_button)
          .append($upload_filename)
          .append($upload_status)
      )
      .append($progress);
    $cancel_button.click(function () {
      ajax.abort();
      $upload_div.remove();
    });
    ajax.$upload_div = $upload_div;
    $('#uploads').append($upload_div);
    ajax.open('POST', '/upload-ajax', true);
    ajax.send(formData);
  });
});
