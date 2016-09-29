<%inherit file="/base.mako"/>
<%!
from operator import itemgetter
%>

<%def name="title()">
  Environment Variables
</%def>

<%def name="more_css()">
  .block-span { display: block; }
  .to-right { margin-right: 10px; }
</%def>

<%block name="main">
  <div class="panel panel-info">
    <div class="panel-heading">
      <h3 class="panel-title">Env</h3>
    </div>
    <div class="panel-body">
      <h4><a href="${ url_for('app.get_app', name=app.name) }">${ app.name }</a></h4>
      <p>设置环境变量, 这些变量会被设置进容器里的环境变量并且在启动程序的时候继承下来.</p>
      <p>注意, 环境变量无法叫做 "env". 另外环境变量会自动变为大写值, 如 "karazhan" 变成 "KARAZHAN"</p>
    </div>
  </div>

  % for env in envs:
    <%
      env_content = sorted(env.items(), key=itemgetter(0))
    %>
    <div class="panel panel-info">
      <div class="panel-heading">
        <h3 class="panel-title">${ env.envname }
          <a name="resize" class="btn-xs pull-right" href="#"><span class="fui-resize"></span></a>
        </h3>
      </div>
      <div class="panel-body hidden">
        <form class="form-horizontal" action="${ url_for('app.app_env', name=app.name) }" method="POST">
          <input type="hidden" name="env" value="${ env.envname }">
          % for key, value in env_content:
            <div class="form-group">
              <div class="col-sm-5">
                <input class="form-control key" type="text" name="key_${ key }" value="${ key }">
              </div>
              <span>:</span>
              <div class="col-sm-1 pull-right">
                <button class="btn btn-xs btn-warning"><span class="fui-trash"></span></button>
              </div>
              <div class="col-sm-5 pull-right">
                <input class="form-control value" type="text" name="value_${ key }" value="${ value }">
              </div>
            </div>
          % endfor
        </form>
        <a name="delete-env" class="btn btn-warning pull-right to-right" href="#" data-env="${ env.envname }"><span class="fui-trash"></span> Delete Env</a>
        <a name="submit-env" class="btn btn-info pull-right to-right" href="#"><span class="fui-check"></span> OK</a>
        <a name="add-row" class="btn btn-info pull-right to-right" href="#"><span class="fui-plus"></span> Add Row</a>
      </div>
    </div>
  % endfor

  <div class="col-sm-8 col-sm-offset-8">
    <div class="col-sm-4">
      <input type="text" class="form-control" name="new_env" value="">
    </div>
    <button class="btn btn-info">Add Env</button>
  </div>

</%block>

<%def name="bottom_script()">
  <textarea id="env-line" class="hidden">
    <div class="form-group">
      <div class="col-sm-5">
        <input class="form-control key" type="text" name="" value="">
      </div>
      <span>:</span>
      <div class="col-sm-1 pull-right">
        <button class="btn btn-xs btn-warning"><span class="fui-trash"></span></button>
      </div>
      <div class="col-sm-5 pull-right">
        <input class="form-control value" type="text" name="" value="">
      </div>
    </div>
  </textarea>

  <textarea id="env-form" class="hidden">
    <div class="panel panel-info">
      <div class="panel-heading">
        <h3 class="panel-title">{env}
          <a name="resize" class="btn-xs pull-right" href="#"><span class="fui-resize"></span></a>
        </h3>
      </div>
      <div class="panel-body">
        <form class="form-horizontal" action="/app/{name}/env" method="POST">
          <input type="hidden" name="env" value="{env}">
            <div class="form-group">
              <div class="col-sm-5">
                <input class="form-control key" type="text" name="" value="">
              </div>
              <span>:</span>
              <div class="col-sm-1 pull-right">
                <button class="btn btn-xs btn-warning"><span class="fui-trash"></span></button>
              </div>
              <div class="col-sm-5 pull-right">
                <input class="form-control value" type="text" name="" value="">
              </div>
            </div>
        </form>
        <a name="delete-env" class="btn btn-warning pull-right to-right" href="#" data-env="{env}"><span class="fui-trash"></span> Delete Env</a>
        <a name="submit-env" class="btn btn-info pull-right to-right" href="#"><span class="fui-check"></span> OK</a>
        <a name="add-row" class="btn btn-info pull-right to-right" href="#"><span class="fui-plus"></span> Add Row</a>
      </div>
    </div>
  </textarea>

  <script>

    var env_tmpl = $('#env-line').val();
    var form_tmpl = $('#env-form').val();

    $(document).on('click', 'a[name=resize]', function(e) {
      e.preventDefault();
      var body = $(this).parent().parent().siblings('.panel-body');
      if (body.is(':hidden')) {
        body.removeClass('hidden').show();
      } else {
        body.hide();
      }
    }).on('click', 'button.btn.btn-xs', function(e){
      e.preventDefault();
      if (confirm('确定删除么')) {
        $(this).parent().parent().remove();
      }
    });

    $(document).on('keyup', 'input.key', function(){
      var value = $(this).val().toUpperCase();
      $(this).val(value);
      $(this).attr('name', 'key_' + value);
      $(this).closest('.form-group').find('input.value').attr('name', 'value_' + value);
    });

    $(document).on('click', 'a[name=add-row]', function(e){
      e.preventDefault();
      var form = $(this).siblings('form');
      form.append(env_tmpl);
    });

    $(document).on('click', 'a[name=delete-env]', function(e){
      e.preventDefault();
      if (!confirm('确认删除么? 无法恢复的哈')) {
        return;
      }
      var self = $(this);
      var env = self.data('env');
      $.post('/ajax/app/${ app.name }/delete-env', {env: env}, function(){
        self.parent().parent().remove();
      });
    });

    $(document).on('click', 'a[name=submit-env]', function(e){
      e.preventDefault();
      if (!confirm('确认提交么? 会覆盖原有配置')) {
        return;
      }
      $(this).siblings('form').submit();
    });

    $('button.btn-info').click(function(e){
      e.preventDefault();
      var env = $(this).siblings('div').find('input[name=new_env]').val();
      if (env === '') {
        alert('Env 名字不能为空');
        return;
      }
      var form = form_tmpl.replace(/{env}/g, env).replace(/{name}/g, '${ app.name }');
      $('div.panel.panel-info:last').after(form);
    });
  </script>
</%def>
