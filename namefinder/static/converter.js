let input = document.getElementById("input")
let result = document.getElementById("result")

function normalizeForCuneiform(text){
    let l="()?-[]x+’'°§⸢⸣*./-"
	for (let c of l){
		while (text.includes(c)){
			text=text.replace(c,"")
		}
	}
	// remove <i> from text
	while (text.includes("<i>")){
		text=text.replace("<i>","")
	}
	// split text  into words take the first word
	let words = text.split(" ")
	let firstword = words[0]
	return firstword;
}


function convertWordtoCuneiform(word){
	word=normalizeForCuneiform(word)
	let shaped = shaper(word)
		let text = ""
		for (i of shaped){
			text+=convertCuneiform(i)
		}
		return text
	
}


function convertCuneiform(sy){
	let space = ""
	if(sy==""){
		return ""
	}
	if(sy=="_"){
		return " "
	}
	for (i of unicodeData){
		let val = i.values.map(el=>{return el.toLowerCase()})
		if (val.includes(sy)){
			return i.unicode
		}
	}
	if (sy.length==3){
		h1=sy.slice(0,2)
		h2=sy.slice(1,3)
		h1=convertCuneiform(h1)
		h2=convertCuneiform(h2)
		return h1+h2
	}	
	else{
		return "-"
	}
}

let sesliler = ["a","e","i","u"]

function shaper(word){
	word=word.toLowerCase()
	let shaped = ""
	for (i of word){
		if (sesliler.includes(i)){
			shaped+="V"
		}
		else{
			shaped+="C"	
		}
	}
	let result=hecele([[],shaped])
	let heceler = []
	let start = 0
	for (i of result){
		l=i.length
		heceler.push(word.slice(start,l+start))
		start+=l
	}
	return heceler
}


function hecele(shaped){
	syls=shaped[0]
	shaped=shaped[1]
	if (shaped.length==0){
		return syls
	}
	else if(shaped.slice(0,4)=="CVCC" | shaped=="CVC"){
		syls.push("CVC")
		return hecele([syls,shaped.slice(3)])
	}

	else if(shaped.slice(0,2)=="CV"){
		syls.push("CV")
		return hecele([syls,shaped.slice(2)])
	}

	else if(shaped.slice(0,3)=="VCV"){
		syls.push("V")
		return hecele([syls,shaped.slice(1)])
	}

	else if(shaped.slice(0,2)=="VC"){
		syls.push("VC")
		return hecele([syls,shaped.slice(2)])
	}
}


