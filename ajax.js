function submit(data, url) {
  return new Promise((resolve, reject) => {
    //data.ICStateNum=this.icCount.next().value;
    let formIframe=document.createElement('iframe');
    formIframe.name='formIframe';
    formIframe.width=0; 
    formIframe.height=0; 
    formIframe.style='display: none';
    let form=document.createElement('form');
    form.method='post'; 
    form.target='_self'; 
    form.action=url;
    Object.keys(data).map((key) => {
      let input=document.createElement('input');
      input.type='hidden'; 
      input.name=key; 
      input.value=data[key];
      form.appendChild(input);
    });
    uiFrame.contentDocument.body.appendChild(formIframe);
    formIframe.contentDocument.body.appendChild(form);
    formIframe.onload= () => {
      resolve(formIframe.contentDocument);
      if (userOption.debug) 
       targetFrame.contentDocument.documentElement.innerHTML=formIframe.contentDocument.documentElement.innerHTML; 
      uiFrame.contentDocument.body.removeChild(formIframe);
      formIframe=null;
    }
    form.submit();
  });
}

function  paraTeachingTimetable(subject = 'UGEB') {
    return {
        'CLASS_SRCH_WRK2_ACAD_CAREER': userCareer,
        'CLASS_SRCH_WRK2_STRM$50$': userTermCode,
        'CU_RC_TMSR801_SUBJECT': subject,
        'ICAction': 'CU_RC_TMSR801_SSR_PB_CLASS_SRCH',
    };
}

function para_timetable() {
    return {
        'DERIVED_CLASS_S_START_DT': userTermDate,
        'ICAction': 'DERIVED_CLASS_S_SSR_REFRESH_CAL',
    }
}

function init() {
	icCount=getICCount(targetDocument.getElementsByName('ICStateNum')[0].value);
	trashIframe=document.createElement('iframe');
	trashIframe.width=0;
	trashIframe.height=0;
	trashIframe.style='display: none';
	targetDocument.children[0].appendChild(trashIframe);
}

function* getICCount(icInit) {
	for (let i=Number(icInit);true;i++) {
		yield i;
	}
}

function submitForm(data, callback) {
    function jsToForm(obj) {
        return Object.keys(obj).map((key) => {
            return encodeURIComponent(key) + '=' + encodeURIComponent(obj[key]);
        }).join('&');
    }
    function loadedHandlerPass() {
        if (this.readyState==4 && this.status!=200)
            alert('network error. please report this bug.');
    }
    function loadedHandlerCallback(callback) {
        if (this.readyState==4)
            if (this.status==200)
                callback(this.responseXML);
            else
                alert('network error. please report this bug.');
    }
    let xhttp = new XMLHttpRequest();
    if (callback == undefined)
        xhttp.onreadystatechange=loadedHandlerPass();
    else
        xhttp.onreadystatechange=loadedHandlerCallback();
    xhttp.open('POST', targetDocument.win0.action, true);
    xhttp.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhttp.responseType='document';
    xhttp.send(jsToForm(data));
    return xhttp;
}