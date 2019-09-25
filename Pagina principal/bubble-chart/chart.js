

$(document).ready(function () {


  console.log(researchAreas);
   AssignFontSize(18,28,researchAreas);

   var bubbleChart = new d3.svg.BubbleChart({
    supportResponsive: true,
    //container: => use @default
    size: 600,
    viewBoxSize: 600,
    innerRadius: 140,
    outerRadius: 400,
    radiusMin: 24,
    radiusMax: 15,
    intersectDelta: 0,
    intersectInc:0,
    // circleColor: '#ff0000',
    data: {
      items: researchAreas,
      eval: function (item) {return item.count;},
      classed: function (item) {return item.text.split(" ").join("");}
    },
    plugins: [
      {
        name: "central-click",
        options: {
          text: "(Ver más...)",
          style: {
            "font-size": "18px",
            "font-style": "italic",
            "font-family": "Source Sans Pro, sans-serif",
            //"font-weight": "700",
            "text-anchor": "middle",
            "fill": "Black"
          },
          attr: {dy: "70px"},
          centralClick: function(node) {
            
            window.location.href = urlsBase+"/individual?uri="+node.uri;
           
          }
        }
      },
      {
        name: "lines",
        options: {
          format: [
            {// Line #0
              textField: "short",
              classed: {count: true},
              style: {
                "font-size": "0px",
                "font-family": "Source Sans Pro, sans-serif",
                "text-anchor": "middle",
                fill: "black",
                "font-weight":"bold"

                
              },
              attr: {
                dy: "6px",
                x: function (d) {return d.cx;},
                y: function (d) {return d.cy;}
              }
            },
            {// Line #1
              textField: "count",
              classed: {tspan: true},
              style: {
                "font-size": "0px",
                "font-family": "Source Sans Pro, sans-serif",
                "text-anchor": "middle",
                fill: "black",
                visibility:"hidden"
              },
              attr: {
                dy: "8px",
                x: function (d) {return d.cx;},
                y: function (d) {return d.cy;},
                
              }
            },
            {// Line #2
              textField: "N",
              classed: {tspan: true},
              style: {
                "font-size": "0px",
                "font-family": "Source Sans Pro, sans-serif",
                "text-anchor": "middle",
                fill: "black",
                visibility:"hidden"
                
              },
              attr: {
                dy: "10px",
                x: function (d) {return d.cx;},
                y: function (d) {return d.cy;},
                
              }
            }
          ],
          centralFormat: [
            {// Line #0
              textField:"text",
              style: {
                "font-size": "24px",
                "font-weight":"bold"
              },
              attr: { dy: "-20px",}
            },
            {// Line #1
              textField:"count",
              style: {
                "font-size": "30px",
                visibility:"visible"
            },
              attr: {dy: "15px"}
            },
            {// Line #2
              textField: "N",
              classed: {tspan: true},
              style: {
                "font-size": "24px",
                "font-family": "Source Sans Pro, sans-serif",
                "text-anchor": "middle",
                fill: "black",
                visibility:"visible"
                
              },
              attr: {
                dy: "40px",
                x: function (d) {return d.cx;},
                y: function (d) {return d.cy;},
                
              }
            }
          ]
        }
      }]
  });
});

function AssignFontSize(minFontsize,maxFontSize, researchAreas)
{
  maxValue= researchAreas[0]['count'];
  minValue= researchAreas[researchAreas.length-1]['count'];

  for(var i =0;i <researchAreas.length;i++)
  {
    // Se asigna un tamaño de fuente adecuado al tamaño del circulo
    researchAreas[i]['fontSize']=(researchAreas[i]['count']- minValue) * (maxFontSize-minFontsize)/(maxValue-minValue)+minFontsize; 
    
    
    // Se calcula la abreviacion que se mostrará cuando el circulo sea pequeño
    var fullText= researchAreas[i]['text'];
    
    if(fullText.length>0)
    {
      var abreviation="";
      var noSNI= fullText.split("(")[0];
      var words = noSNI.trim();
      words=words.split(" ");
      console.log(words);
      if(words.length>1)
      {
        for(var w = 0;w <words.length;w++)
        {
          if(words[w].length>3 || (words[w][0]>='0'&& words[w][0]<='9'))
           abreviation= abreviation.concat(words[w][0].toUpperCase());
        }
        // console.log("length > 1");
      }
      else{ 
        abreviation = words[0].substr(0,Math.min(3,words[0].length-1)).toUpperCase();
      }
      
      
      researchAreas[i]['text']=noSNI;
      researchAreas[i]['short']= abreviation;
    }
    
  


  }



}
function SetAbreviation(researchAreas)
{
  

}