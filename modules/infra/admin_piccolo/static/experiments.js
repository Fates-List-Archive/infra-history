class ExperimentList {
    constructor(expList) {
        this.expList = expList
    }

    hasExperiment(exp) {
        let hasExperiment = false
        this.expList.forEach(el => {
            if(el.id == exp.id) {
                hasExperiment = true
            }
        })
        info("Root", "Has experiment:", exp, hasExperiment)
        return hasExperiment
    }
}

class UserExperiments {
    // These are the supported experiments by lynx
    static Unknown = new UserExperiments(0)
    static LynxExperimentRolloutView = new UserExperiments(2)
  
    constructor(id) {
      this.id = id
    }

    static from(expList) {
        info("Root", "Experiment list:", expList)
        let properExpList = []
        Object.keys(UserExperiments).forEach(exp => {
            info("Root", `Found experiment ${exp} with id ${UserExperiments[exp].id}`)
            if(expList.includes(UserExperiments[exp].id)) {
                info("Root", `Adding experiment ${exp}`)
                properExpList.push(UserExperiments[exp])
            }
        })

        return new ExperimentList(properExpList)
    }
}  

readyModule("experiments")