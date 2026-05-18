const SUPABASE_URL="https://hcuorfjumfurcxrvvsmw.supabase.co";
const SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhjdW9yZmp1bWZ1cmN4cnZ2c213Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg1MTM4OTYsImV4cCI6MjA5NDA4OTg5Nn0.9gGg0d7YTWyMhGlIE8KebDisRQi8V1jprLfXc3lT2jE";

const grid=document.getElementById("servicesGrid");
const modal=document.getElementById("modal");
const select=document.getElementById("planSelect");
const price=document.getElementById("priceValue");
const buy=document.getElementById("buyBtn");

let map={};
let current="";

const IMG_BASE="https://hcuorfjumfurcxrvvsmw.supabase.co/storage/v1/object/public/";

async function load(){

const res=await fetch(`${SUPABASE_URL}/rest/v1/products?select=*`,{
headers:{
apikey:SUPABASE_KEY,
Authorization:`Bearer ${SUPABASE_KEY}`
}
});

const data=await res.json();

map={};

data.forEach(p=>{
if(!map[p.name]) map[p.name]=[];
map[p.name].push(p);
});

render();
}

function render(){
grid.innerHTML="";

Object.keys(map).forEach(name=>{
const first=map[name][0];

const img = first.image?.startsWith("http")
? first.image
: IMG_BASE + first.image;

const div=document.createElement("div");
div.className="card";

div.innerHTML=`
<img src="${img}">
<h3>${name}</h3>
`;

div.onclick=()=>open(name);

grid.appendChild(div);
});
}

function open(name){
current=name;
modal.classList.remove("hidden");

select.innerHTML="";

map[name].forEach((p,i)=>{
const opt=document.createElement("option");
opt.value=i;
opt.textContent=p.duration;
select.appendChild(opt);
});

update(0);
select.onchange=e=>update(e.target.value);
}

function update(i){
const p=map[current][i];
price.textContent=p.price;

buy.href=`https://wa.me/9613177862?text=Order ${current} ${p.duration} ${p.price}`;
}

document.getElementById("cancelBtn").onclick=()=>{
modal.classList.add("hidden");
};

load();
