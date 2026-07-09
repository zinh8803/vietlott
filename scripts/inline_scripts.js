=== Script 15 ===
   var PortalSiteId='main.frontend.vi';   function CreateRenderInfo()   {       SiteId='main.frontend.vi';       SiteLang='vi';       ORenderInfo = Vietlott.Utility.WebEnvironments.ServerSideFrontEndCreateRenderInfo(SiteId).value;       ORenderInfo.SiteLang = SiteLang;       return ORenderInfo;   }   function callSweetSuccess(description)   {       $.toast({           position: 'top-right',           heading: 'Thông báo',           text: description,           allowToastClose: true,           stack: false,           icon: 'success'       })   }   function callSweetError(description)   {       $.toast({           position: 'top-right',           heading: 'Thông báo',           text: description,           allowToastClose: true,           stack: false,           icon: 'error'       })   }   function callSweetInfo(description)   {       $.toast({           position: 'top-right',           heading: 'Thông báo',           text: description,           allowToastClose: true,           stack: false,           icon: 'info'       })   }   function callSweetAlert(description)   {       $.toast({           position: 'top-right',           heading: 'Thông báo',           text: description,           allowToastClose: true,           stack: false,           icon: 'warning'       })   }   var JsPageTitle='Vietlott - XEM CHI TIẾT KẾT QUẢ Bingo18';

========================================

=== Script 16 ===
 function ScrollTop()    {        var body = $("html, body");           body.stop().animate({scrollTop:0}, '100', 'swing', function() {        });   } 

========================================

=== Script 17 ===


========================================

=== Script 18 ===
     function CallSearch()     {         RenderInfo = CreateRenderInfo();         Keyword = document.getElementById('txtSearchKeyword').value.trim();         if(Keyword=='')         {             alert('Chưa nhập từ khóa tìm kiếm');             return;         }         AjaxOut = Vietlott.PlugIn.WebParts.NavBarWebPart.ServerSideSearch(RenderInfo, Keyword).value;         if(AjaxOut.Error)         {             alert(AjaxOut.InfoMessage);             return;         }         window.open(AjaxOut.RetUrl,'_self');     } 

========================================

=== Script 20 ===
    $('#aspnetForm').on('keyup keypress', function(e) {      var keyCode = e.keyCode || e.which;      if (keyCode === 13) {         e.preventDefault();        return false;      }    }); 

========================================

=== Script 21 ===


        $('.date').datetimepicker({

            language: 'en',

            format: "dd/mm/yyyy",

            weekStart: 1,

            todayBtn: 1,

            autoclose: 1,

            todayHighlight: 1,

            startView: 2,

            minView: 2,

            forceParse: 0

        });

    

========================================

=== Script 23 ===


  window.dataLayer = window.dataLayer || [];

  function gtag(){dataLayer.push(arguments);}

  gtag('js', new Date());



  gtag('config', 'UA-42453093-1');



========================================
