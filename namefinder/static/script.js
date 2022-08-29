// materilize scripts

document.addEventListener('DOMContentLoaded', function() {
	var elems = document.querySelectorAll('.collapsible');
	var instances = M.Collapsible.init(elems);
});
document.addEventListener('DOMContentLoaded', function() {
    var elems = document.querySelectorAll('select');
    var instances = M.FormSelect.init(elems);
  });

let modal = document.getElementById("modal1");
let modalContent = document.getElementById("modal-content");



document.addEventListener("DOMContentLoaded", function () {
	var elems = document.querySelectorAll(".modal");
	var instances = M.Modal.init(elems);
});

// csrf setup
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');
axios.defaults.headers.post['X-CSRFToken'] = csrftoken;


let datadiv = document.getElementById("data");
let datadiv2 = document.getElementById("data2");
datadiv2.style.display="none"

let types={deity:"purple",person:"blue",place:"green"}


function createTags(data){
	datadiv.innerHTML=""
	for (let i of data) {
		nameclean = i.name_clean;
		newname = document.createElement("a");
		newname.id = "name-" + i.name_id;
		newname.className = `btn col s3 ${types[i.type]} ${i.type} ${i.writing_clean} ${i.completeness} lighten-2 white-text`;
		newname.innerHTML = `${nameclean}`;
		newname.addEventListener("click", (e) => {
			detail(i.name_id);
		});
		datadiv.append(newname);
	}	
}

function detail(index) {
	// make axios get request to get the data of the index from api/detail/index/ and store data in obj
	axios.get(`api/detail/${index}/`) // get the data of the index from api/detail/index/
		.then(res => {
			console.log(res.data);
			detailMaker(res.data);
			
		})
	function detailMaker(obj){
		var instance = M.Modal.getInstance(modal);
		let attes=obj["instances"]
		obj = obj["name"]
		modalContent.innerHTML = `
		<ul class="collection with-header">
		<li class="collection-header"><h4 class="center-align"><sup>${obj["det_1"]}</sup>${obj["name_clean"]} (${obj["type"]})</h4></li>
		${CuneiformMaker(obj)}
		</ul>
		<ul class="collection" ></ul>
		${corresMaker(obj)}
		${VariantMaker(obj)}
		${LiteratureMaker(obj)}
		${attesmaker(attes)}
		`
		instance.open();
	}
	
}


let initialData;

// make axios get request to get data from server /api/tags/100/ and store it in InitialData
axios.get('/api/tags/1000/')	.then(function (response) {
	initialData = response.data;
	createTags(initialData);
})


/* 
let allAttes={}
for (let [index, i] of data.entries()) {
	let obj = data[index]
	let attes=obj["Attestation"].split(";|")
	for (a of attes){
		let at = a.split(" ")
		at = at[0]+" "+at[1]
		if (at in allAttes){
			allAttes[at].push(obj.Name_clean)
			allAttes[at]=[...new Set(allAttes[at])]
		}else{
			allAttes[at]=[obj.Name_clean]
		}
	}


}

for(tablet of Object.keys(allAttes).sort().slice(4)){
	let newname = document.createElement("a");
	newname.className = `btn col s3 brown lighten-2 white-text`;
	newname.id=`tablet-${tablet}`
	newname.innerHTML = `${tablet}`;
	newname.addEventListener("click", (e) => {
		detailTablet(e)
	});
	datadiv2.append(newname);

}

*/
function detailTablet(e) {
	var instance = M.Modal.getInstance(modal);
	let obj = e.currentTarget.innerHTML
	let modalText = `
	<ul class="collection with-header">
	<li class="collection-header"><h4 class="center-align">${obj}</h4></li>
	</ul>
	`
	modalContent.innerHTML=modalText
	let ul = document.createElement("ul")
	ul.className="collection"
	for (i of allAttes[obj]){
		console.log(i)
		let li = document.createElement("li")
		li.className="collection-item"
		let link = document.createElement("a")
		link.innerHTML=i
		li.appendChild(link)
		let index = ""
		for (let a of datadiv.children){
			if(a.text==i){
			index = a.id.split("-")[1];
			break;
			} 
		}
		li.addEventListener("click",e=>{
			detail(data[index])
		})

		ul.appendChild(li)
	}
	modalContent.appendChild(ul)
	instance.open();
}



let searchName = document.getElementById("searchNames")
let searchTablet = document.getElementById("searchTablets")

let regexSearch = document.getElementById("regexSearch")
let normalSearch = document.getElementById("normalSearch")
let searchMethod = true

regexSearch.addEventListener("click",e=>{
	regexSearch.classList.add("disabled")
	normalSearch.classList.remove("disabled")
	searchMethod= true

})
normalSearch.addEventListener("click",e=>{
	normalSearch.classList.add("disabled")
	regexSearch.classList.remove("disabled")
	searchMethod= false

})
searchTablet.addEventListener("click",e=>{
	searchTablet.classList.add("disabled")
	searchName.classList.remove("disabled")
	datadiv2.style.display=""
	datadiv.style.display="none"

})

searchName.addEventListener("click",e=>{
	searchTablet.classList.remove("disabled")
	searchName.classList.add("disabled")
	datadiv2.style.display="none"
	datadiv.style.display=""

})



function removeConsecutiveDuplicates(text){
	if (text.length<2){
		return text
	}
	if (text[0]!=text[1]){
		return text[0] + removeConsecutiveDuplicates(text.slice(1))
	}
	return removeConsecutiveDuplicates(text.slice(1))


}


function normalize (text){
    text=text.toLowerCase().trim();
    text=text.replace(/í/g,"i")
    text=text.replace(/g/g,"k")
    text=text.replace(/b/g,"p")
    text=text.replace(/ì/g,"i")
    text=text.replace(/ú/g,"u")
    text=text.replace(/á/g,"a")
    text=text.replace(/é/g,"e")
    text=text.replace(/š/g,"s")
    text=text.replace(/ḫ/g,"h")
    text=text.replace(/d/g,"t")
    text=text.replace(/j/g,"y")
    text=text.replace(/ia/g,"ya")
    text=removeConsecutiveDuplicates(text)
    return text

}

function normalize2(text){
    let l="()?-[]x+’'°§⸢⸣*./"
	for (let c of l){
		while (text.includes(c)){
			text=text.replace(c,"")
		}
	}
    text=removeConsecutiveDuplicates(text)
	return text;
}



function CuneiformMaker(obj){
	try {

		let text = convertWordtoCuneiform(obj.name_clean)
		if (text){
			return `<li class="collection-header center-align cuneiform"> ${text}</li>`
		}else{
			return ""
		}
	}catch{
		return ""
	}

}


function attesmaker(attes){
	console.log(attes)
	let text=""
	text+=`
	<h5>Attestations</h5>
	<ul class="collection">`
	let exists=false;
	for (i of attes){
		let occurrence = i["occurrence"]
		if (occurrence!=""){
			let ctn = occurrence.split(" ")
			let link = `https://www.hethport.uni-wuerzburg.de/hetkonk/hetkonk_abfrage.php?p=${ctn[0]}%20${ctn[1]}`
			exists=true
			text+=`<li class="collection-item">${i.name} : <a href="${link}" target="_blank">${occurrence} </a></li>`
		}
	}
	text+=`</ul>`

	if (exists){

		return text
	}else{
		return ""
	}
}

function LiteratureMaker(obj){
	if (obj["literature"]){
		text=`<h5>Literature & Notes</h5>
	<ul class="collection" ></ul>
	<span>${obj["literature"]}</span>`
		return	text}
	else{
		return ""
	}
}
function VariantMaker(obj){
	if (obj["variant_forms"]){
		text=`<h5>Variant forms</h5>
	<ul class="collection" ></ul>
	<span>${obj["variant_forms"]}</span>`
		return	text}
	else{
		return ""
	}
}

function corresMaker(obj){
	if(obj["correspondence"]){
		let text =`<h5>Correspondences</h5>
	<ul class="collection" ></ul>
	<span>${obj["correspondence"]}</span>`
		return text

	}
	else{
		return ""}
}

let type_all = document.getElementById("type_all")
let type_dn= document.getElementById("type_dn")
let type_pn= document.getElementById("type_pn")
let type_gn= document.getElementById("type_gn")
let spel_all= document.getElementById("spel_all")
let spel_phon= document.getElementById("spel_phon")
let spel_logo= document.getElementById("spel_logo")
let spel_akk= document.getElementById("spel_akk")
let comp_all= document.getElementById("comp_all")
let comp_acep= document.getElementById("comp_acep")
let comp_incomp= document.getElementById("comp_incomp")

let tips= [type_pn,type_dn,type_gn,type_all]
let spels = [spel_phon,spel_akk,spel_logo,spel_all]
let comps = [comp_all,comp_acep,comp_incomp]

let filterArray = ["all","all","all"]


function filterNames(){
	let elements = document.getElementsByClassName(filterArray.join(" "))
	elements= Array.from(elements)
	for (i of datadiv.children) {
		if (elements.indexOf(i)==-1) {
			i.style.display="none"
		}

	}
}



function filters(index,key,e,arr){
	arr.forEach(e=>{e.classList.remove("disabled")})
	filterArray[index]=key
	e.currentTarget.classList.add("disabled")
	searchTags()
}


type_dn.addEventListener("click",e=>{
	filters(0,"deity",e,tips)
})

type_pn.addEventListener("click",e=>{
	filters(0,"person",e,tips)
})

type_gn.addEventListener("click",e=>{
	filters(0,"place",e,tips)
})

type_all.addEventListener("click",e=>{
	filters(0,"all",e,tips)
})

spel_all.addEventListener("click",e=>{
	filters(1,"all",e,spels)
})

spel_logo.addEventListener("click",e=>{
	filters(1,"logographic",e,spels)
})

spel_phon.addEventListener("click",e=>{
	filters(1,"phonetic",e,spels)
})
spel_akk.addEventListener("click",e=>{
	filters(1,"akkadographic",e,spels)
})
comp_all.addEventListener("click",e=>{
	filters(2,"all",e,comps)
})
comp_acep.addEventListener("click",e=>{
	filters(2,"acephalous",e,comps)
})
comp_incomp.addEventListener("click",e=>{
	filters(2,"incomplete",e,comps)
})

let search = document.getElementById("search");

search.addEventListener("input", searchTags);



function searchTags() {
	let search = document.getElementById("search").value;
	search = normalize(search);
	if (searchMethod==false){
		search=normalize2(search)
	}
	let data = {query: search, regex: searchMethod, type: filterArray[0], spel: filterArray[1], comp: filterArray[2]};
	console.log(data)
	
	axios.post('/api/search/', data) .then(function (response) {
		createTags(response.data);
	}	)

}