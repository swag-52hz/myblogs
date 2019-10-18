$(function () {
  let $login = $('.form-contain');  // 获取登录表单元素

  // for test
  // console.log(document.referrer);   // 将referrer url 打印到终端

  // 登录逻辑
  $login.submit(function (e) {
    // 阻止默认提交操作
    e.preventDefault();

    // 获取用户输入的账号信息
    let sUserAccount = $("input[name=telephone]").val();  // 获取用户输入的用户名或者手机号
    // 判断用户输入的账号信息是否为空
    if (sUserAccount === "") {
      message.showError('用户账号不能为空');
      return
    }
    // 判断输入手机号格式或者用户名格式是否正确
    if (!(/^1[345789]\d{9}$/).test(sUserAccount) && !(/^\w{5,20}$/).test(sUserAccount)) {
      message.showError('请输入合法的用户账号：5-20个字符的用户名或者11位手机号');
      return
    }

    // 获取用户输入的密码
    let sPassword = $("input[name=password]").val();  // 获取用户输入的密码
    // 判断用户输入的密码是否为空
    if (!sPassword) {
      message.showError('密码不能为空');
      return
    }
    // 判断用户输入的密码是否为6-20位
    if (sPassword.length < 6 || sPassword.length > 20) {
      message.showError('密码的长度需在6～20位以内');
      return
    }

    // 获取用户是否勾许"记住我"，勾许为true，不勾许为false
    let bStatus = $("input[type='checkbox']").is(":checked");  // 获取用户是否选择记住我，勾上代表true，没勾上代码false

    // 发起登录请求
    // 创建请求参数
    let SdataParams = {
      "user_account": sUserAccount,
      "password": sPassword,
      "remember_me": bStatus
    };

    // 创建ajax请求
    $.ajax({
      // 请求地址
      url: "/users/login/",  // url尾部需要添加/
      // 请求方式
      type: "POST",
      data: JSON.stringify(SdataParams),
      // 请求内容的数据类型（前端发给后端的格式）
      contentType: "application/json; charset=utf-8",
      // 响应数据的格式（后端返回给前端的格式）
      dataType: "json",
    })
      .done(function (res) {
        if (res.errno === "0") {
          // 注册成功
          message.showSuccess('恭喜你，登录成功！');
          setTimeout(function () {
            let sCurrentUrl = $(location).attr("href");
          if (sCurrentUrl.indexOf('?next=') !== -1){
            let sDomain = window.location.origin;
            window.location.href = sDomain + sCurrentUrl.split('=')[1];
          }else{
            // 注册成功之后重定向到打开登录页面之前的页面
            window.location.href = document.referrer;
          }
          }, 800)
        } else {
          // 登录失败，打印错误信息
          message.showError(res.errmsg);
        }
      })
      .fail(function(){
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