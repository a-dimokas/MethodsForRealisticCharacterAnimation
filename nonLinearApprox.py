import bpy
import math
import numpy as np
from scipy.optimize import minimize
from math import dist

#the blender home directory is needed for the project (eg: C:\\Users\\----\\Blender)
blenderHomeDir = ""

#model's data
outputName = None
maxFrames = None
maxBones = None
objName = None
fileName = None

#(-1,-1) for all verts
vertsDebug = [1804,1862]

#if we want to continue operations from a previous output result, this variable is for the ftol used in the previous resutls
reloadOutput = None

#specify ftol and maxIterations for the lbfgs method
ftol = None
maxiter = None

#fills empty array with global vertData of frame
def getVerts(realVertData, frame):
    realVerts = open(blenderHomeDir+"\\globalVertices\\"+fileName+"\\vert"+str(frame)+".txt")
    for pos,line in enumerate(realVerts):
        if(pos>vertsDebug[0]):
            tmpArr = line.split(",")
            vx = float(tmpArr[0])
            vy = float(tmpArr[1])
            vz = float(tmpArr[2])
            realVertData.append(np.array([vx,vy,vz]))
        if(pos==vertsDebug[1]):
            break
        
#get restPose vertices
restVerts = open(blenderHomeDir+"\\restPoseVerts\\"+fileName+"\\verts.txt")
restVertData = []
for pos,line in enumerate(restVerts):
    if(pos>vertsDebug[0]):
        tmpArr = line.split(",")
        vx = float(tmpArr[0])
        vy = float(tmpArr[1])
        vz = float(tmpArr[2])
        restVertData.append(np.array([vx,vy,vz,1.]))
    if(pos==vertsDebug[1]):
        break
      
#random weight init, same as the init of the linear approx system
def randomWeights():
    vertexGroupFile = open(blenderHomeDir+"\\weights\\"+fileName+"\\weights.txt")
    vertexGroups = []
    for p,l in enumerate(vertexGroupFile):
        if(p>vertsDebug[0]):
            vertGroups = l[1:l.find(']')].split(',')
            for i in range(len(vertGroups)):
                vertGroups[i] = int(vertGroups[i])
            vertexGroups.append(vertGroups)  
        if(p==vertsDebug[1]):
            break
    vertexGroupFile.close()
    weights = [] 
    weightFile = open(blenderHomeDir+"\\initialRandomWeights\\"+outputName+"\\Weights.txt")
    for p,l in enumerate(weightFile):
        weight = l.split(',')
        for i in range(len(weight)):
            weight[i] = float(weight[i])
        weights.append(weight)
    weightFile.close()
    return weights, vertexGroups

#correct weights init
def correctWeights():
    weightFile = open(blenderHomeDir+"\\weights\\"+fileName+"\\weights.txt")
    weights = [] 
    vertexGroups = []
    for p,l in enumerate(weightFile):
        if(p>vertsDebug[0]):
            vertGroups = l[1:l.find(']')].split(',')
            w = []
            for i in range(len(vertGroups)):
                vertGroups[i] = int(vertGroups[i])
            weight = l[l.find(']')+4:(len(l)-2)].split(',')
            w = np.array([])
            for i in weight:
                w = np.append(w,float(i))
            vertexGroups.append(vertGroups)  
            weights.append(w)
        if(p==vertsDebug[1]):
            break
    weightFile.close()
    return weights, vertexGroups

#b contains the real vertex, each line is a frame, each column is a vertex index
b = []
for frame in range(1,maxFrames+1):
    realVertData = []
    getVerts(realVertData, frame)
    b.append(realVertData)
    

#initilizations
weights, vertexGroups = randomWeights()
#weights, vertexGroups = correctWeights()
#x0 init List
initList = []

weightLength = 0
for w in weights:
    if(len(w)>1):
        weightLength += len(w)
    #add the weights to the init list
        for i in w:
            initList.append(i)

bones = []
for i in vertexGroups:
    for j in i:
        if j not in bones:
            bones.append(j)
bones.sort()

B = len(bones)
N = len(restVertData)
P = maxFrames

#get initial bone transformation matrices
def initialBones(initL, frame):
    boneMat = []
    boneFile = open(blenderHomeDir+"\\initialBones\\"+outputName+"\\frame"+str(frame)+".txt")
    for p,l in enumerate(boneFile):
        initL.append(float(l))
        
for i in range(1,P):
   initialBones(initList, i)

#this fucntion is to continue from a previous output of the nonLinear approx
def reloadPreviousInits(initL):
    inputFile = open(blenderHomeDir+"\\nonLinApprox\\"+outputName+"\\output"+reloadOutput+".txt")
    for p,l in enumerate(inputFile):
        initL.append(float(l))
        
# if we use this we dont need to use previous initList
# reloadPreviousInits(initList) 

#calculate objective function of LBFGS
def f(x):
    sumF = 0
    for frame in range(maxFrames-1):
        wInd = [0]
        for v in range(len(vertexGroups)):
            sumF += dist(vertApprox(x,frame,v,wInd), b[frame][v])
    weightInd = 0
    for v in range(len(vertexGroups)): #len(restVertData)):
        if(len(vertexGroups[v])>1):
            sumF += 100*(sum(x[weightInd:weightInd+len(vertexGroups[v])]) - 1)**2
            weightInd += len(vertexGroups[v])
    return sumF

#calculating approximation of vertices with init List
def vertApprox(x,p,vv,wInd):
    sum = [0,0,0]
    if(len(vertexGroups[vv])>1):
        for i in range(len(vertexGroups[vv])):
            bonePos = weightLength+12*p*B + bones.index(vertexGroups[vv][i])*12
            sum = np.add(sum, (x[wInd[0]] * np.matmul(
            [[x[bonePos],x[bonePos+1],x[bonePos+2],x[bonePos+3]],
            [x[bonePos+4],x[bonePos+5],x[bonePos+6],x[bonePos+7]],
            [x[bonePos+8],x[bonePos+9],x[bonePos+10],x[bonePos+11]]],
            restVertData[vv])))
            wInd[0] += 1
        return sum
    else:
        bonePos = weightLength+12*p*B + bones.index(vertexGroups[vv][0])*12
        sum = np.matmul(
        [[x[bonePos],x[bonePos+1],x[bonePos+2],x[bonePos+3]],
        [x[bonePos+4],x[bonePos+5],x[bonePos+6],x[bonePos+7]],
        [x[bonePos+8],x[bonePos+9],x[bonePos+10],x[bonePos+11]]],
        restVertData[vv])
        return sum
   

print("from iter 0, " + fileName + str(vertsDebug) + str(ftol))
#contains the result of LBFGS algorithm
result = minimize(f, initList, options={'disp':True, 'maxfun':2000000, 'maxiter':maxiter, 'ftol':ftol}, method="L-BFGS-B", jac=None)

#output result to file
with open(blenderHomeDir+"\\nonLinApprox\\"+outputName+"\\output"+str(ftol)+".txt", "w") as fileOutput:
    for i in result.x:
        fileOutput.write(str(i) + "\n")