$(function () {

  // ================== 修改用户组 ================
  let $groupsBtn = $("#btn-pub-news");
  $groupsBtn.click(function () {
    // 判断用户组名是否为空
    let sName = $("#news-title").val();  // 获取用户组名
    if (!sName) {
      message.showError('请填写用户组名！');
      return
    }

    // 判断是否选择权限
    let sGroupPermissions = $("#group-permissions").val();
    if (!sGroupPermissions || sGroupPermissions === []) {
      message.showError('请选择权限');
      return
    }


    // 获取coursesId 存在表示更新 不存在表示发表
    let groupsId = $(this).data("news-id");
    let url = groupsId ? '/admin/groups/' + groupsId + '/' : '/admin/groups/add/';
    let data = {
      "name": sName,
      "group_permissions": sGroupPermissions

    };

    $.ajax({
      // 请求地址
      url: url,
      // 请求方式
      type: groupsId ? 'PUT' : 'POST',
      data: JSON.stringify(data),
      // 请求内容的数据类型（前端发给后端的格式）
      contentType: "application/json; charset=utf-8",
      // 响应数据的格式（后端返回给前端的格式）
      dataType: "json",
    })
      .done(function (res) {
        if (res.errno === "0") {
          if (groupsId) {
            fAlert.alertNewsSuccessCallback("用户组更新成功", '跳到用户组管理页', function () {
              window.location.href = '/admin/groups/'
            });

          } else {
            fAlert.alertNewsSuccessCallback("用户组创建成功", '跳到用户组管理页', function () {
              window.location.href = '/admin/groups/'
            });
          }
        } else {
          fAlert.alertErrorToast(res.errmsg);
        }
      })
      .fail(function () {
        message.showError('服务器超时，请重试！');
      });

  });


  // get cookie using jQuery
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      let cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        let cookie = jQuery.trim(cookies[i]);
        // Does this cookie string begin with the name we want?
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
  }

  // Setting the token on the AJAX request
  $.ajaxSetup({
    beforeSend: function (xhr, settings) {
      if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
      }
    }
  });

});
